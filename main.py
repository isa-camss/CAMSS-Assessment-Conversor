import os
import re
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

    '''
    #for the moment, criteria ids are taken from conversiontables.csv
    def generate_dict(self, v: str):
        if v not in self.dic_criteria:
            self.dic_criteria[v] = []
        for s, p, o in self.g.triples((URIRef(SC + v), CAV.includes, None)):
            for s_, p_, o_ in self.g.triples((URIRef(SC + str(o).split("#")[-1]), CCCEV.hasDescription, None)):
                self.dic_criteria[v] = (o, o_)
    '''

    def load_criteria(self):
        self.csv = open('conversiontables.csv', 'r')
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


def set_name(file_path: str):
    # name format of EIF 300 and 310 scenarios
    pattern1 = re.compile(
        r'CAMSS[\s\-\_]Assessment(\_?EIF\sScenario-?)?[\s\-\_](of[\s\-\_])?([^\_]+)(\_?EIF\s?Scenario\_?)?\_?v\.?1')
    # name format of EIF
    pattern3 = re.compile(r'CAMSS[\_\-\s]Ontology')
    # search for patterns
    name = file_path.strip()
    name1 = pattern1.search(name)
    name3 = pattern3.search(name)
    if name1:
        return name1.group(3)
    elif name3:
        return 'CAMSS_Assessments_graph'
    else:
        return name


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
    id_ass: str = ''
    sc510_id: str = "87c1faa38c024ef8225a36b2c5d472986ac937ab61b86d8e80edd5468c4eab28"
    tool_version: str
    sub_g: Graph = Graph()
    dict_crit: dict = Scenario().dic_criteria
    dict_responses: dict = {'stmt': ['None'] * 44, 'score': ['None'] * 44, 'criteria': ['None'] * 44}
    responses_old: list = [0, 0, 0, 0]  # number of not answered, n/a, no, yes responses
    responses_new: list = [0, 0, 0, 0]  # number of not answered, n/a, no, yes responses
    g_scores: dict = {}

    def __init__(self, file_path: str):
        self.filepath = file_path
        self.set_graph()
        # self.filepath = self.set_name(file_path)
        self.ttl_filename = set_name(file_path[:-4].split("/")[-1])
        # self.set_id_ass()
        # self.set_eif_version()
        return

    def set_graph(self):
        """
        Reads a ttl file and transforms it to an rdflib graph instance.
        :param file_path:
        :return:
        """
        data = open(self.filepath, 'rb')
        self.g = Graph()
        self.g.parse(data, format='ttl')
        data.close()
        return

    def set_sub_graph(self, file_path: str):
        data = open(file_path, 'rb')
        self.sub_g = Graph()
        self.sub_g.parse(data, format='ttl')
        data.close()
        return

    def set_eif_version(self):
        """
        Sets the version of the CAMSS EIF scenario used to perform the assessment.
        Not executed when working with the assessments graph.
        :return:
        """
        self.eif_version = \
            str(self.g.value(URIRef(CAMSSA + self.id_ass, CAMSSA), CAV.contextualisedBy, None)).split("#")[-1]
        return

    def set_id_ass(self):
        """
        Sets the identifier of the individual assessment.
        This method also allows to identify the individual assessment (identifier) when working with the assessments
        graph.
        :return:
        """
        self.id_ass = str(self.g.value(predicate=RDF.type, object=CAV.Assessment, any=False)).split("/")[-1]
        return

    def match_scoring(self, score):
        if self.eif_version != Scenario.v500:
            if score == "0":
                # 0 means Negative response
                return "20"
            elif score == "1":
                # 1 means Positive response
                self.responses_new[3] += 1
                return "100"
            elif score == "2":
                # 2 means N/A
                self.responses_new[1] += 1
                return "100"
        else:
            return score

    def add_results_subgraph(self):
        """
        Adds new subgraphs. This method complements the overwrite_graph method.
        :return:
        """
        for index in range(len(self.dict_responses['criteria'])):
            # Score
            score_uri = URIRef(CAMSSA + str(uuid.uuid4()), CAMSSA)
            # score_uri = URIRef(CAMSSA + id_score, CAMSSA) if id_score else URIRef(CAMSSA + str(uuid.uuid4()), CAMSSA)
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
            ass_uri = URIRef(CAMSSA + self.id_ass, CAMSSA)
            self.g.add((ass_uri, CAV.resultsIn, statement_uri))
        return

    def remove_old_subgraph(self):
        """
        Removes either a subgraph contained in an assessment graph, or an assessment graph from the assessments graph.
        :return:
        """
        for s, p, o in self.g.triples((URIRef(CAMSSA + self.id_ass, CAMSSA), CAV.resultsIn, None)):
            # original identifier of the criterion score (old CAMSS EIF scenario)
            id_score = str(self.g.value(subject=o, predicate=CAV.refersTo, any=None)).split("/")[-1]
            # remove sub_graph
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
        :return:
        """
        # Save to file
        destination = 'arti/out/' + self.ttl_filename + f'/'
        os.makedirs(destination, exist_ok=True)
        self.g.serialize(format="turtle", destination=destination + self.ttl_filename + ".ttl")
        return
        # return self.ttl_filename

    def bind_graph(self):
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
        :return: the larger graph resulting from the merging
        """
        # modify the scenario version identifier
        self.g.set((URIRef(CAMSSA + self.id_ass, CAMSSA), CAV.contextualisedBy, URIRef(SC + self.sc510_id, SC)))
        # modify dates
        self.g.set(
            (URIRef(CAMSSA + self.id_ass, CAMSSA), CAMSS.assessmentDate, Literal(None, datatype=URIRef(XSD.date))))
        self.g.set(
            (URIRef(CAMSSA + self.id_ass, CAMSSA), CAMSS.submissionDate, Literal(None, datatype=URIRef(XSD.date))))
        # modify the CAMSS EIF scenario version
        self.g.set((URIRef(CAMSSA + self.id_ass, CAMSSA), CAMSS.toolVersion, URIRef(TOOL + "5.1.0", TOOL)))
        return

    def populate_dict_responses(self):
        # s stands for subject, p stands for predicate, o stands for object
        for s, p, o in self.g.triples((URIRef(CAMSSA + self.id_ass, CAMSSA), CAV.resultsIn, None)):
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
            if id_criterion in self.dict_crit[self.eif_version] and len(duplicated_id_criterion) > 1:
                while len(duplicated_id_criterion) > 0:
                    # equivalent identifier of the criterion
                    equiv_id_criterion = self.dict_crit[self.sc510_id][duplicated_id_criterion.pop()]
                    index = self.dict_crit[self.sc510_id].index(equiv_id_criterion)
                    self.dict_responses['stmt'][index] = statement
                    self.dict_responses['score'][index] = self.match_scoring(str(score))
                    self.dict_responses['criteria'][index] = equiv_id_criterion
                    # self.add_results_subgraph(statement, score, equiv_id_criterion)
            elif id_criterion in self.dict_crit[self.eif_version]:
                # equivalent identifier of the criterion
                equiv_id_criterion = self.dict_crit[self.sc510_id][self.dict_crit[self.eif_version].index(id_criterion)]
                index = self.dict_crit[self.sc510_id].index(equiv_id_criterion)
                self.dict_responses['stmt'][index] = statement
                self.dict_responses['score'][index] = self.match_scoring(str(score))
                self.dict_responses['criteria'][index] = equiv_id_criterion
                # self.add_results_subgraph(statement, score, equiv_id_criterion)
            # if tool version 500, no changes needed
        # generate the list of unfilled criteria that need to be created
        unfilled_criteria = [i for i, x in enumerate(self.dict_crit[self.eif_version]) if
                             x == '']
        for i in unfilled_criteria:
            index = self.dict_crit[self.sc510_id].index(self.dict_crit[self.sc510_id][i])
            self.dict_responses['stmt'][index] = 'None'
            self.dict_responses['score'][index] = '100'
            self.dict_responses['criteria'][index] = self.dict_crit[self.sc510_id][i]
            # self.add_results_subgraph(id_criterion=self.dict_crit[self.sc510_id][i])
        # check A2
        if utils.get_score_from_criterionA2(utils.set_graph(self.filepath), self.dict_crit[self.eif_version][1]) in [0,
                                                                                                                     2]:
            self.dict_responses['stmt'][2] = 'None'
            self.dict_responses['score'][2] = '0'

    def set_old_scores(self):
        # generate scores
        # scores
        self.g_scores[self.ttl_filename] = []
        # old scores for v300 and v310: automated and strength
        list_ans_old = utils.get_ass_scores(utils.set_graph(self.filepath))
        total_old = len(list_ans_old)
        self.responses_old = [0,  # number of not answered, in old version of EIF Scenario this field is always 0
                              sum([1 for i in list_ans_old if i == 2]),  # number of n/a
                              sum([1 for i in list_ans_old if i == 0]),  # number of negative answers
                              sum([1 for i in list_ans_old if i == 1])  # number of positive answers
                              ]
        self.g_scores[self.ttl_filename].append(
            round((self.responses_old[3]) / (total_old - self.responses_old[1]) * 100))
        self.g_scores[self.ttl_filename].append(
            round(((self.responses_old[3] + self.responses_old[2]) / total_old) * 100))

    def set_new_scores(self):
        # new scores
        list_ans_new = utils.get_ass_scores(utils.set_graph(f'arti/out/{self.ttl_filename}/{self.ttl_filename}.ttl'))
        total_new = 44 - (1 if self.dict_responses['score'][2] == '0' else 0)
        unfilled_criteria = [i for i, x in enumerate(self.dict_crit[self.eif_version]) if
                             x == '']
        self.responses_new[1] += len(unfilled_criteria)
        self.responses_new[2] = sum([1 for i in list_ans_new if i == 20])
        self.g_scores[self.ttl_filename].append(
            round(self.responses_new[3] / (total_new - self.responses_new[1]) * 100))
        self.g_scores[self.ttl_filename].append(
            round(((self.responses_new[3] + self.responses_new[2]) / total_new) * 100))
        return self.g


def run(param: str = 'arti/in/'):
    """
    Use it to run the code from a python console, Jupyter Lab or Notebook, etc.
    """
    main()
    return


def main():
    # input folder of the individual assessment graphs and the assessments graph
    input_folder = 'arti/in'
    # output folder of all updated graphs
    os.makedirs('arti/out/', exist_ok=True)
    # assessment graph constructor
    # # option 1
    # final_ass_graph = GraphInstance(glob.glob(input_folder + '/AssessmentsG' + '/*')[0])
    # list of individual assessment files
    list_ass_names = [path for path in glob.iglob(input_folder + '/**', recursive=False) if
                      path != input_folder + "/AssessmentsG"]
    # option 2
    list_ass = []
    # this loop works on all individual assessment files
    # that is, ttl files of the individual assessment graphs and assessments graph
    for path in list_ass_names:
        # name of the file
        # head = set_name(path[:-4].split("/")[-1])
        # individual assessment graph constructor
        # CAMSS EIF scenario version of the working graph
        # assessment graph identifier
        new_graph = GraphInstance(path)
        # output folder of the updated individual assessment graph
        new_dir = 'arti/out/' + new_graph.ttl_filename + f'/'
        os.makedirs(new_dir, exist_ok=True)
        # assessment id, scenario version, tool version
        new_graph.set_id_ass()
        new_graph.set_eif_version()
        new_graph.tool_version = \
        str(new_graph.g.value(URIRef(CAMSSA + new_graph.id_ass, CAMSSA), CAMSS.toolVersion, any=None)).split("#")[-1]
        print(f"Extracting and initialising migration of the {new_graph.ttl_filename} "
              f"CAMSS Assessment EIF {new_graph.tool_version}")
        # updating of the individual assessment graph and the assessments graph
        new_graph.overwrite_graph()
        # initialise list of new responses
        new_graph.responses_new = [0, 0, 0, 0]
        # updating RDF file
        new_graph.populate_dict_responses()
        new_graph.set_old_scores()
        new_graph.remove_old_subgraph()
        new_graph.add_results_subgraph()
        # bind namespaces
        new_graph.bind_graph()
        # # option 1
        # final_ass_graph.sub_g = new_graph
        # final_ass_graph.eif_version = final_ass_graph.sub_g.eif_version
        # final_ass_graph.id_ass = final_ass_graph.sub_g.id_ass
        # final_ass_graph.overwrite_graph(final_ass_graph.sub_g.id_ass)
        # option 2
        list_ass.append(new_graph)
        # serialisation of the updated individual assessment graph
        new_graph.serialize()
        new_graph.set_new_scores()
        # create csv with scores
        utils.get_punct(new_graph.g_scores)
    # option 2
    final_ass_graph = GraphInstance(glob.glob(input_folder + '/AssessmentsG' + '/*')[0])
    print(f"Extracting and initialising migration of the {final_ass_graph.ttl_filename} dataset")
    print("       Migration IN PROGRESS")
    print("")
    for ass in list_ass:
        final_ass_graph.set_sub_graph('arti/out/' + f'{ass.ttl_filename}/' + ass.ttl_filename + '.ttl')
        final_ass_graph.eif_version = ass.sc510_id
        final_ass_graph.id_ass = ass.id_ass
        final_ass_graph.overwrite_graph()
        final_ass_graph.remove_old_subgraph()
        final_ass_graph.g += final_ass_graph.sub_g
        print(f"       Migration of {ass.ttl_filename} COMPLETED")
        print("")

    # output folder of the assessments graph
    # serialisation of the updated assessments graph
    # option 1 and 2
    final_ass_graph.serialize()
    print("")
    print("")
    print("You may find the CAMSS Assessments graph in the 'out/CAMSS_Assessments_graph' folder")


# main function
if __name__ == '__main__':
    main()
