import os, warnings
import glob
import uuid
import requests
from rdflib import URIRef, Literal, Namespace, Graph
from rdflib.namespace import RDF, OWL, XSD
import utils

warnings.filterwarnings('ignore')
# assessment(s) graph namespaces, apart from RDF, OWL and XSD
CAMSS = Namespace("http://data.europa.eu/2sa#")
CAMSSA = Namespace("http://data.europa.eu/2sa/assessments/")
CAV = Namespace("http://data.europa.eu/2sa/cav#")
CSSV_RSC = Namespace("http://data.europa.eu/2sa/cssv/rsc/")
SC = Namespace("http://data.europa.eu/2sa/scenarios#")
SCHEMA = Namespace("http://schema.org/")
STATUS = Namespace("http://data.europa.eu/2sa/rsc/assessment-status#")
TOOL = Namespace("http://data.europa.eu/2sa/rsc/toolkit-version#")


class Scenario:
    """
    This class generates a dictionary of scenario identifiers and criteria identifiers per scenario
    """
    dic_criteria: dict = {}
    v300: str = "3aadede3d912d8ab2b20d40221274da3af8f9ee9c14f0e1226f9217a3e8953e4"
    v310: str = "44119b394568e5be30da9b83729a3cba1f19eadd53373d5cc6ff6a73fd3e26e8"
    v500: str = "f717f525751d9de54fc478770a2fb1845767ec01f1661d602383ae868d2bb5b7"
    v510: str = "87c1faa38c024ef8225a36b2c5d472986ac937ab61b86d8e80edd5468c4eab28"

    def __init__(self):
        self.csv = None
        self.load_criteria()
        return

    def load_criteria(self):
        """
        This method creates a dictionary of criteria per scenario.
        :return: sets the criteria dictionary
        """
        self.csv = open('migrationtables.csv', 'r')
        self.dic_criteria[self.v300] = []
        self.dic_criteria[self.v310] = []
        self.dic_criteria[self.v500] = []
        self.dic_criteria[self.v510] = []
        for line in self.csv:
            line = line.rstrip()
            ids = line.split(",")
            self.dic_criteria[self.v300].append(ids[1])
            self.dic_criteria[self.v310].append(ids[2])
            self.dic_criteria[self.v500].append(ids[3])
            self.dic_criteria[self.v510].append(ids[4])
        self.csv.close()
        return


class GraphInstance:
    """
    A graph instance of an individual assessment graph and of the assessments graph. This class allows to read,
    modify and convert graphs to the latest version of the CAMSS EIF scenario. It also allows to serialise graphs
    to a tll file.
    """
    g: Graph
    ttl_filename: str
    filepath: str
    eif_version: str = ''
    ass_id: str = ''
    sc510_id: str = "87c1faa38c024ef8225a36b2c5d472986ac937ab61b86d8e80edd5468c4eab28"
    tool_version: str
    dict_crit: dict = Scenario().dic_criteria
    dict_responses: dict = {'stmt': ['None'] * 44, 'old_score': ['None'] * 44, 'score': ['None'] * 44, 'criteria': ['None'] * 44, 'answer': ['None'] * 44}
    responses_new: list = [None, None, None, None]  # number of not answered, n/a, no, yes responses
    responses_new_df: dict = {}
    g_scores: dict = {}

    def __init__(self, file_path: str):
        self.filepath = file_path
        self.set_graph()
        self.ttl_filename = utils.set_name(file_path[:-4].split("/")[-1])
        return

    def set_graph(self):
        """
        Reads a ttl file and transforms it to an rdflib graph instance.
        :return: sets the graph
        """
        try:
            data = open(self.filepath, 'rb')
            self.g = Graph()
            self.g.parse(data, format='turtle')
        except RuntimeWarning:
            breakpoint()
        data.close()
        return

    def set_eif_version(self):
        """
        Sets the version of the CAMSS EIF scenario used to perform the assessment.
        Not executed when working with the assessments graph.
        :return: sets the CAMSS Assessment EIF Scenario version
        """
        self.eif_version = \
            str(self.g.value(URIRef(CAMSSA + self.ass_id, CAMSSA), CAV.contextualisedBy, None)).split("#")[-1]
        return

    def set_ass_id(self):
        """
        Sets the identifier of the individual assessment.
        This method also allows to identify the individual assessment (identifier) when working with the assessments
        graph.
        :return: sets the Assessment identifier
        """
        self.ass_id = str(self.g.value(predicate=RDF.type, object=CAV.Assessment, any=False)).split("/")[-1]
        return

    def match_scoring(self, score):
        """
        Matching scores from v3.0.0 and v3.1.0 to v5.1.0 of the CAMSS Assessment EIF Scenario.
        :param score: old score from v3.0.0 and v3.1.0 of the CAMSS Assessment EIF Scenario
        :return: the score value in v5.1.0 of the CAMSS Assessment EIF Scenario
        """
        if self.eif_version != Scenario.v500:
            if score == "0":
                # 0 means Negative response
                return "20"
            elif score == "1":
                # 1 means Positive response
                return "100"
            elif score == "2":
                # 2 means N/A
                return "100"
        else:
            return score

    def add_results_subgraph(self):
        """
        Adds new subgraphs. This method complements the overwrite_graph method.
        :return: addition of a specific subgraph
        """
        for index in range(len(self.dict_responses['criteria'])):
            # Score
            score_uri = URIRef(CAMSSA + str(uuid.uuid4()), CAMSSA)
            self.g.add((score_uri, RDF.type, CAV.Score))
            self.g.add((score_uri, RDF.type, OWL.NamedIndividual))
            self.g.add((score_uri, CAV.value, Literal(self.dict_responses['score'][index], datatype=XSD.int)))
            self.g.add((score_uri, CAV.assignedTo, URIRef(SC + 'c-' + self.dict_responses['criteria'][index], SC)))
            # Statement
            statement_uri = URIRef(CAMSSA + str(uuid.uuid4()), CAMSSA)
            self.g.add((statement_uri, RDF.type, CAV.Statement))
            self.g.add((statement_uri, RDF.type, OWL.NamedIndividual))
            self.g.add((statement_uri, CAV.refersTo, score_uri))
            self.g.add((statement_uri, CAV.judgement, Literal(self.dict_responses['stmt'][index], lang='en')))
            # Assessment
            ass_uri = URIRef(CAMSSA + self.ass_id, CAMSSA)
            self.g.add((ass_uri, CAV.resultsIn, statement_uri))
        return

    def remove_old_subgraph(self):
        """
        Removes either a subgraph contained in an assessment graph, or an assessment graph from the assessments graph.
        :return: removal of a specific subgraph
        """
        for s, p, o in self.g.triples((URIRef(CAMSSA + self.ass_id, CAMSSA), CAV.resultsIn, None)):
            # original identifier of the criterion score (old CAMSS EIF scenario)
            id_score = str(self.g.value(subject=o, predicate=CAV.refersTo, any=None)).split("/")[-1]
            # remove old results
            self.g.remove((s, p, o))
            # remove old statements
            self.g.remove((o, None, None))
            # remove old scores
            self.g.remove((URIRef(CAMSSA + id_score, CAMSSA), None, None))
        return

    def serialize(self):
        """
        Serialises to a ttl file in a specific folder locally.
        :return: serialization completed
        """
        # Save to file
        if self.ttl_filename == 'CAMSS_Assessments_graph':
            destination = f'arti/out/{self.ttl_filename}/'
            os.makedirs(destination, exist_ok=True)
            self.g.serialize(format="turtle", destination=destination + self.ttl_filename + ".ttl")
        else:
            destination = 'arti/out/'
            self.g.serialize(format='turtle', destination=destination + f'EIF-5.1.0-CAMSSAssessment_{self.ttl_filename}.ttl')
        return

    def bind_graph(self):
        """
        This method allows to ensure that all URIs are well-defined.
        :return: graph binding completed
        """
        self.g.bind('camss', CAMSS, replace=True)
        self.g.bind('cav', CAV, replace=True)
        self.g.bind('camssa', CAMSSA, replace=True)
        self.g.bind('cssvrsc', CSSV_RSC, replace=True)
        self.g.bind('status', STATUS, replace=True)
        self.g.bind('tool', TOOL, replace=True)
        self.g.bind('sc', SC, replace=True)
        self.g.bind('schema', SCHEMA, replace=True)
        return

    def overwrite_graph(self):
        """
        Overwrites certain content of the individual assessment graphs or the assessments graph.
        :return: graph resulting after some modifications
        """
        # modify the scenario version identifier
        self.g.set((URIRef(CAMSSA + self.ass_id, CAMSSA), CAV.contextualisedBy, URIRef(SC + self.sc510_id, SC)))
        # modify dates
        self.g.set(
            (URIRef(CAMSSA + self.ass_id, CAMSSA), CAMSS.assessmentDate, Literal(None, datatype=URIRef(XSD.date))))
        self.g.set(
            (URIRef(CAMSSA + self.ass_id, CAMSSA), CAMSS.submissionDate, Literal(None, datatype=URIRef(XSD.date))))
        # modify the CAMSS EIF scenario version
        self.g.set((URIRef(CAMSSA + self.ass_id, CAMSSA), CAMSS.toolVersion, URIRef(TOOL + "5.1.0", TOOL)))
        return

    def populate_dict_responses(self):
        """
        This method populates the dictionary of responses from the old Assessment. Mapping of criteria.
        :return: population of the dictionary of responses
        """
        # s stands for subject, p stands for predicate, o stands for object
        for s, p, o in self.g.triples((URIRef(CAMSSA + self.ass_id, CAMSSA), CAV.resultsIn, None)):
            # original statement for a specific criterion (old CAMSS EIF scenario)
            statement = self.g.value(subject=o, predicate=CAV.judgement, any=None)
            # original identifier of the criterion score (old CAMSS EIF scenario)
            id_score = str(self.g.value(subject=o, predicate=CAV.refersTo, any=None)).split("/")[-1]
            # original criterion score (old CAMSS EIF scenario)
            score = self.g.value(subject=URIRef(CAMSSA + id_score, CAMSSA), predicate=CAV.value, any=None)
            # original identifier of the criterion (old CAMSS EIF scenario)
            id_criterion = str(self.g.value(subject=URIRef(CAMSSA + str(id_score), CAMSSA), predicate=CAV.assignedTo,
                                            any=None)).split("/")[-1].split("c-")[-1]
            # create sub_graph
            # id_score is maintained
            #
            duplicated_id_criterion = [i for i, x in enumerate(self.dict_crit[self.eif_version]) if
                                       x == id_criterion]
            if self.tool_version in ['3.0.0', '3.1.0']:
                if id_criterion in self.dict_crit[self.eif_version] and len(duplicated_id_criterion) > 1:
                    while len(duplicated_id_criterion) > 0:
                        # equivalent identifier of the criterion
                        equiv_id_criterion = self.dict_crit[self.sc510_id][duplicated_id_criterion.pop()]
                        index = self.dict_crit[self.sc510_id].index(equiv_id_criterion)
                        self.dict_responses['stmt'][index] = statement
                        self.dict_responses['old_score'][index] = str(score)
                        self.dict_responses['score'][index] = self.match_scoring(str(score))
                        self.dict_responses['criteria'][index] = equiv_id_criterion
                        if self.dict_responses['old_score'][index] == "0":
                            self.dict_responses['answer'][index] = 'No/Gradient'
                        elif self.dict_responses['old_score'][index] == "1":
                            self.dict_responses['answer'][index] = 'Yes/Gradient'
                        elif self.dict_responses['old_score'][index] == "2":
                            self.dict_responses['answer'][index] = 'Not Applicable'
                        else:
                            self.dict_responses['answer'][index] = 'Not Answered'
                        # self.add_results_subgraph(statement, score, equiv_id_criterion)
                elif id_criterion in self.dict_crit[self.eif_version]:
                    # equivalent identifier of the criterion
                    equiv_id_criterion = self.dict_crit[self.sc510_id][self.dict_crit[self.eif_version].index(id_criterion)]
                    index = self.dict_crit[self.sc510_id].index(equiv_id_criterion)
                    self.dict_responses['stmt'][index] = statement
                    self.dict_responses['old_score'][index] = str(score)
                    self.dict_responses['score'][index] = self.match_scoring(str(score))
                    self.dict_responses['criteria'][index] = equiv_id_criterion
                    if self.dict_responses['old_score'][index] == "0":
                        self.dict_responses['answer'][index] = 'No/Gradient'
                    elif self.dict_responses['old_score'][index] == "1":
                        self.dict_responses['answer'][index] = 'Yes/Gradient'
                    elif self.dict_responses['old_score'][index] == "2":
                        self.dict_responses['answer'][index] = 'Not Applicable'
                    else:
                        self.dict_responses['answer'][index] = 'Not Answered'
                    # self.add_results_subgraph(statement, score, equiv_id_criterion)
            else:
                if id_criterion in self.dict_crit[self.eif_version]:
                    # equivalent identifier of the criterion
                    equiv_id_criterion = self.dict_crit[self.sc510_id][
                        self.dict_crit[self.eif_version].index(id_criterion)]
                    index = self.dict_crit[self.sc510_id].index(equiv_id_criterion)
                    self.dict_responses['stmt'][index] = statement
                    self.dict_responses['old_score'][index] = str(score)
                    self.dict_responses['score'][index] = self.match_scoring(str(score))
                    self.dict_responses['criteria'][index] = equiv_id_criterion
                    if self.dict_responses['old_score'][index] == "20":
                        self.dict_responses['answer'][index] = 'No/Gradient'
                    elif self.dict_responses['old_score'][index] == "0":
                        self.dict_responses['answer'][index] = 'Not Answered'
                    else:
                        self.dict_responses['answer'][index] = 'Yes/Gradient or Not Applicable'
            # if tool version 500, no changes needed
        # check A2
        if self.dict_responses['old_score'][1] in ["0", "2"]:
            self.dict_responses['stmt'][2] = 'None'
            self.dict_responses['score'][2] = '0'
            self.dict_responses['answer'][2] = 'None'
        # check A33
        if self.tool_version in ['3.0.0', '3.1.0']:
            self.dict_responses['stmt'][33] = "The specification is associated with EIRA ABB's in the EIRA Library " \
                                              "of Interoperability Specifications (ELIS).\n\n" \
                                              "ELIS link:\n" \
                                              "https://joinup.ec.europa.eu/collection/common-assessment-method-standards-and-specifications-camss/solution/elis/release/v500"
            if self.dict_responses['old_score'] in ['0', '2']:
                self.dict_responses['score'][33] = '100'
                self.dict_responses['answer'][33] = 'Yes/Gradient'
        # generate the list of unfilled criteria that need to be created
        unfilled_criteria = [i for i, x in enumerate(self.dict_crit[self.eif_version]) if
                             x == '']
        for i in unfilled_criteria:
            index = self.dict_crit[self.sc510_id].index(self.dict_crit[self.sc510_id][i])
            self.dict_responses['stmt'][index] = 'None'
            self.dict_responses['score'][index] = '100'
            self.dict_responses['criteria'][index] = self.dict_crit[self.sc510_id][i]
            if self.dict_responses['old_score'][index] == "0":
                self.dict_responses['answer'][index] = 'No/Gradient'
            elif self.dict_responses['old_score'][index] == "1":
                self.dict_responses['answer'][index] = 'Yes/Gradient'
            elif self.dict_responses['old_score'][index] == "2":
                self.dict_responses['answer'][index] = 'Not Applicable'
            elif self.dict_responses['old_score'][index] == "None":
                self.dict_responses['answer'][index] = 'Not Applicable'
            else:
                self.dict_responses['answer'][index] = 'Not Answered'

    def set_old_scores(self):
        """
        This method generates the old automated Score and the assessment strength.
        :return: dictionary of old scores
        """
        # generate scores
        # scores
        self.g_scores[self.ttl_filename] = []
        # old scores for v300 and v310: automated and strength
        total_old = len(self.dict_responses['old_score'])
        responses_old = [0,  # number of not answered, in old version of EIF Scenario this field is always 0
                         sum([1 for i in self.dict_responses['old_score'] if i == "2"]),  # number of n/a
                         sum([1 for i in self.dict_responses['old_score'] if i == "0"]),  # number of negative answers
                         sum([1 for i in self.dict_responses['old_score'] if i == "1"])  # number of positive answers
                         ]
        self.g_scores[self.ttl_filename].append(
            round((responses_old[3]) / (total_old - responses_old[1]) * 100))
        self.g_scores[self.ttl_filename].append(
            round(((responses_old[3] + responses_old[2]) / total_old) * 100))

    def set_new_scores(self):
        """
        This method generates the new automated Score and the assessment strength.
        :return: dictionary of old scores and new scores
        """
        # new scores
        pos_ans = sum([1 for i in self.dict_responses['answer'] if i == 'Yes/Gradient'])
        neg_ans = sum([1 for i in self.dict_responses['answer'] if i == 'No/Gradient'])
        not_app = sum([1 for i in self.dict_responses['answer'] if i == 'Not Applicable'])
        total_new = 44 - (1 if self.dict_responses['answer'][1] in ['Not Applicable', 'Not answered'] else 0)
        self.g_scores[self.ttl_filename].append(
            round(pos_ans / (total_new - not_app) * 100))
        self.g_scores[self.ttl_filename].append(
            round(((pos_ans + neg_ans) / total_new) * 100))
        # populate the dictionary of new responses where the number of not applicable, negative and positive answers is given
        self.responses_new[0] = 0
        self.responses_new[1] = not_app
        self.responses_new[2] = neg_ans
        self.responses_new[3] = pos_ans


def run(param: str = 'arti/in/'):
    """
    Use it to run the code from a python console, Jupyter Lab or Notebook, etc.
    """
    main()
    return


def main():
    """
    Main function.
    """
    # input folder of the individual assessment graphs and the assessments graph
    input_folder = 'arti/in'
    # output folder of all updated graphs
    os.makedirs('arti/out/', exist_ok=True)
    list_ass_names = [path for path in glob.iglob(input_folder + '/**.ttl', recursive=False) if
                      path != input_folder + "/AssessmentsG"]
    list_ass = []
    # this loop works on all individual assessment files
    # that is, ttl files of the individual assessment graphs and assessments graph
    for path in list_ass_names:
        # individual assessment graph constructor
        # assessment graph constructor
        new_graph = GraphInstance(path)
        # output folder of the updated individual assessment graph
        new_dir = 'arti/out/'
        os.makedirs(new_dir, exist_ok=True)
        # assessment id, scenario version, tool version
        new_graph.set_ass_id()
        new_graph.set_eif_version()
        new_graph.tool_version = \
        str(new_graph.g.value(URIRef(CAMSSA + new_graph.ass_id, CAMSSA), CAMSS.toolVersion, any=None)).split("#")[-1]
        print(f"Extracting and initialising migration of the {new_graph.ttl_filename} "
              f"CAMSS Assessment EIF {new_graph.tool_version}")
        # updating of the individual assessment graph and the assessments graph
        new_graph.overwrite_graph()
        # initialise list of new responses
        new_graph.responses_new = [0, 0, 0, 0]
        # updating RDF file
        new_graph.populate_dict_responses()
        # old scores generation
        if new_graph.tool_version != '5.0.0':
            new_graph.set_old_scores()
        else:
            new_graph.g_scores[new_graph.ttl_filename] = ['Undefined'] * 2
        # removal and addition of subgraph
        new_graph.remove_old_subgraph()
        new_graph.add_results_subgraph()
        # bind namespaces
        new_graph.bind_graph()
        list_ass.append(new_graph)
        # serialisation of the updated individual assessment graph
        new_graph.serialize()
        # new scores generation
        if new_graph.tool_version != '5.0.0':
            new_graph.set_new_scores()
        else:
            new_graph.g_scores[new_graph.ttl_filename] += ['Undefined'] * 2
            new_graph.responses_new[0] = sum([1 for i in new_graph.dict_responses['answer'] if i == 'Not Answered'])
            new_graph.responses_new[2] = sum([1 for i in new_graph.dict_responses['answer'] if i == 'No/Gradient'])
            new_graph.responses_new[1] = 'Undefined'
            new_graph.responses_new[3] = 'Undefined'
        # create csv with scores
        new_graph.responses_new_df[new_graph.ttl_filename] = new_graph.responses_new
        new_graph.g_scores[new_graph.ttl_filename].append(new_graph.tool_version)
        utils.get_punct(new_graph.g_scores, new_graph.responses_new_df)
    # CAMSS Assessment graph constructor
    final_ass_graph = GraphInstance(glob.glob(input_folder + '/AssessmentsG' + '/*')[0])
    print(f"Extracting and initialising migration of the {final_ass_graph.ttl_filename} dataset")
    print("       Migration IN PROGRESS")
    print("")
    for ass in list_ass:
        final_ass_graph.eif_version = ass.sc510_id
        final_ass_graph.ass_id = ass.ass_id
        final_ass_graph.overwrite_graph()
        final_ass_graph.remove_old_subgraph()
        final_ass_graph.g += ass.g
        print(f"       Migration of {ass.ttl_filename} COMPLETED")
        print("")

    # output folder of the assessments graph
    # serialisation of the updated assessments graph
    final_ass_graph.serialize()
    print("")
    print("")
    print("You may find the CAMSS Assessments graph in the 'out/CAMSS_Assessments_graph' folder")


# main function
if __name__ == '__main__':
    main()
