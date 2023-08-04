import os, warnings
import glob
import uuid
from rdflib import URIRef, Literal, Namespace, Graph
from rdflib.namespace import RDF, OWL, XSD
import utils

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
    This class generates a dictionary of scenario identifiers and criteria identifiers per scenario (5.1.0 and 6.0.0).
    """
    dic_criteria: dict = {}
    v510: str = "87c1faa38c024ef8225a36b2c5d472986ac937ab61b86d8e80edd5468c4eab28"
    v600: str = "8022abb075d6aaa372db1471580032cb546e2495fc59d62b0e0df4b8871fe87b"

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
        self.dic_criteria[self.v510] = []
        # other refers to criteria from 5.1.0 that is concatenate with other criteria (criteria merge)
        self.dic_criteria['other'] = []
        self.dic_criteria[self.v600] = []
        for line in self.csv:
            line = line.rstrip()
            ids = line.split(",")
            self.dic_criteria[self.v510].append(ids[1])
            self.dic_criteria['other'].append(ids[2])
            self.dic_criteria[self.v600].append(ids[3])
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
    sc600_id: str = "8022abb075d6aaa372db1471580032cb546e2495fc59d62b0e0df4b8871fe87b"
    tool_version: str
    dict_crit: dict = Scenario().dic_criteria
    dict_responses: dict
    responses_old: list # number of not answered, n/a, no, yes responses
    responses_new: list = [None, None, None, None]  # number of not answered, n/a, no, yes responses
    responses_new_df: dict = {}
    g_scores: dict = {}

    def __init__(self, file_path: str):
        self.filepath = file_path
        self.set_graph()
        self.ttl_filename = utils.set_name(file_path[:-4].split("/")[-1])
        self.dict_responses = {'stmt': ['None'] * 45, 'old_score': ['None'] * 45, 'score': ['None'] * 45,
                                'criteria': ['None'] * 45, 'answer': ['None'] * 45}
        return

    def set_graph(self):
        """
        Reads a ttl file and transforms it to an rdflib graph instance.
        :return: sets the graph
        """
        data = open(self.filepath, 'rb')
        self.g = Graph()
        self.g.parse(data, format='turtle')
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
            self.g.serialize(format='turtle', destination=destination + f'EIF-6.0.0-CAMSSAssessment_{self.ttl_filename}.ttl')
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
        self.g.set((URIRef(CAMSSA + self.ass_id, CAMSSA), CAV.contextualisedBy, URIRef(SC + self.sc600_id, SC)))
        # modify dates
        self.g.set(
            (URIRef(CAMSSA + self.ass_id, CAMSSA), CAMSS.assessmentDate, Literal(None, datatype=URIRef(XSD.date))))
        self.g.set(
            (URIRef(CAMSSA + self.ass_id, CAMSSA), CAMSS.submissionDate, Literal(None, datatype=URIRef(XSD.date))))
        # modify the CAMSS EIF scenario version
        self.g.set((URIRef(CAMSSA + self.ass_id, CAMSSA), CAMSS.toolVersion, URIRef(TOOL + "6.0.0", TOOL)))
        return

    def populate_dict_responses(self):
        """
        This method populates the dictionary of responses from the old Assessment. Mapping of criteria.
        :return: population of the dictionary of responses
        """
        self.responses_old = [0, 0, 0, 0]
        # s stands for subject, p stands for predicate, o stands for object
        for s, p, o in self.g.triples((URIRef(CAMSSA + self.ass_id, CAMSSA), CAV.resultsIn, None)):
            # original statement for a specific criterion (old CAMSS EIF scenario)
            statement = self.g.value(subject=o, predicate=CAV.judgement, any=None)
            # original identifier of the criterion score (old CAMSS EIF scenario)
            id_score = str(self.g.value(subject=o, predicate=CAV.refersTo, any=None)).split("/")[-1]
            # original criterion score (old CAMSS EIF scenario)
            score = self.g.value(subject=URIRef(CAMSSA + id_score, CAMSSA), predicate=CAV.value, any=None)
            # number of not answered, n/a, no, yes responses - from 5.1.0 to 6.0.0, only no responses can be mapped
            if str(score) == "20" or str(score) == "0":
                self.responses_old[2] += 1
            # original identifier of the criterion (old CAMSS EIF scenario)
            id_criterion = str(self.g.value(subject=URIRef(CAMSSA + str(id_score), CAMSSA), predicate=CAV.assignedTo,
                                            any=None)).split("/")[-1].split("c-")[-1]
            # populate dictionary with responses for lately creating subgraph
            if id_criterion in self.dict_crit[self.eif_version]:
                #equivalent criterion id in sc600
                equiv_id_criterion = self.dict_crit[self.sc600_id][
                    self.dict_crit[self.eif_version].index(id_criterion)]
                #dictionary index
                index = self.dict_crit[self.sc600_id].index(equiv_id_criterion)
            elif id_criterion in self.dict_crit['other']:
                equiv_id_criterion = self.dict_crit['other'][self.dict_crit['other'].index(id_criterion)]
                index = self.dict_crit['other'].index(equiv_id_criterion)
            # merging statements for criteria
            if self.dict_responses['stmt'][index] == 'None':
                self.dict_responses['stmt'][index] = statement
            elif self.dict_responses['stmt'][index] != 'None':
                self.dict_responses['stmt'][index] += "\n\n" + statement
            # score mapping from 5.1.0 to 6.0.0
            if self.dict_responses['score'][index] == 'None':
                self.dict_responses['score'][index] = str(score)
            elif self.dict_responses['score'][index] != 'None':
                self.dict_responses['score'][index] += "+" + str(score)
            # mapping of criteria that are preserved in 6.0.0
            if id_criterion not in self.dict_crit['other']:
                self.dict_responses['criteria'][index] = self.dict_crit[self.sc600_id][index]
            if self.dict_responses['old_score'][index] == "20" or self.dict_responses['old_score'][index] == "0":
                self.dict_responses['answer'][index] = 'No/Gradient'
        # population of new criteria - by default, None for statement and 100 (N/A) for score
        unfilled_criteria = [i for i, x in enumerate(self.dict_crit[self.eif_version]) if
                             x == '']
        for i in unfilled_criteria:
            #index = self.dict_crit[self.sc510_id].index(self.dict_crit[self.sc510_id][i])
            index = self.dict_crit[self.sc600_id].index(self.dict_crit[self.sc600_id][i])
            self.dict_responses['stmt'][index] = 'None'
            self.dict_responses['score'][index] = '100'
            #self.dict_responses['criteria'][index] = self.dict_crit[self.sc510_id][i]
            self.dict_responses['criteria'][index] = self.dict_crit[self.sc600_id][i]
            self.dict_responses['answer'][index] = 'Not Applicable'
    def set_old_scores(self):
        """
        This method generates the old automated Score and the assessment strength. Unused in migration from 5.1.0 to 6.0.0.
        :return: dictionary of old scores
        """
        # generate scores
        # scores
        self.g_scores[self.ttl_filename] = []
        # old scores for v300 and v310: automated and strength
        total_old = sum(self.responses_old)
        self.g_scores[self.ttl_filename].append(
            round((self.responses_old[3] / (total_old - self.responses_old[1])) * 100))
        self.g_scores[self.ttl_filename].append(
            round(((self.responses_old[3] + self.responses_old[2]) / total_old) * 100))

    def set_new_scores(self):
        """
        This method generates the new automated Score and the assessment strength. Unused in migration from 5.1.0 to 6.0.0.
        :return: dictionary of old scores and new scores
        """
        # new scores
        pos_ans = sum([1 for i in self.dict_responses['answer'] if i == 'Yes/Gradient'])
        neg_ans = sum([1 for i in self.dict_responses['answer'] if i == 'No/Gradient'])
        not_app = sum([1 for i in self.dict_responses['answer'] if i == 'Not Applicable'])
        total_new = 45 - (1 if self.dict_responses['answer'][1] in ['Not Applicable'] else 0)
        self.g_scores[self.ttl_filename].append(
            round((pos_ans / (total_new - not_app)) * 100))
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
        # conditional unused in migration from 5.1.0 to 6.0.0.
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
        # new scores generation - conditional unused in migration from 5.1.0 to 6.0.0.
        if new_graph.tool_version != '5.0.0':
            new_graph.set_new_scores()
        else:
            new_graph.g_scores[new_graph.ttl_filename] += ['Undefined'] * 2
            #new_graph.responses_new[0] = sum([1 for i in new_graph.dict_responses['answer'] if i == 'Not Answered'])
            new_graph.responses_new[0] = 'Undefined'
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
        final_ass_graph.eif_version = ass.sc600_id
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
