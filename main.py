import os
import glob
import uuid
from rdflib import URIRef, Literal, Namespace, Graph, term
from rdflib.namespace import RDF, OWL, XSD

#assessment(s) graph namespaces, apart from RDF, OWL and XSD
#PCAMSS = Namespace("http://data.europa.eu/2sa#")
CAMSS = Namespace("http://data.europa.eu/2sa#")
CAMSSA = Namespace("http://data.europa.eu/2sa/assessments/")
CAV = Namespace("http://data.europa.eu/2sa/cav#")
CSSV_RSC = Namespace("http://data.europa.eu/2sa/cssv/rsc/")
SC = Namespace("http://data.europa.eu/2sa/scenarios#")
SCHEMA = Namespace("http://schema.org/")
STATUS = Namespace("http://data.europa.eu/2sa/rsc/assessment-status#")
TOOL = Namespace("http://data.europa.eu/2sa/rsc/toolkit-version#")

class Criteria:
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


class GraphInstance:
    """
    A graph instance of an individual assessment graph and of the assessments graph. This class allows to read,
    modify and convert graphs to the latest version of the CAMSS EIF scenario. It also allows to serialise graphs
    to a tll file.
    """
    g: Graph = Graph()
    ttl_filename: str
    eif_version: str = None
    id_ass: str = None
    sc510_id: str = "87c1faa38c024ef8225a36b2c5d472986ac937ab61b86d8e80edd5468c4eab28"
    sub_g: Graph
    dict_crit: dict = Criteria().dic_criteria

    def __init__(self, file_path: str):
        self.set_graph(file_path)
        self.ttl_filename = file_path[:-4].split("/")[-1]
        print(self.ttl_filename)
        return

    def set_graph(self, file_path: str):
        """
        Reads a ttl file and transforms it to an rdflib graph instance.
        :param file_path:
        :return:
        """
        data = open(file_path, 'rb')
        self.g.parse(data, format='ttl')
        data.close()
        self.g.bind("camss", CAMSS, override=True)
        return

    def set_eif_version(self):
        """
        Sets the version of the CAMSS EIF scenario used to perform the assessment.
        Not executed when working with the assessments graph.
        :return:
        """
        self.eif_version = str(self.g.value(URIRef(CAMSSA + self.id_ass, CAMSSA), CAV.contextualisedBy, None)).split("#")[-1]
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
        if self.eif_version != Criteria.v500:
            if score == "0":
                return "20"
            else:
                return "100"
        else:
            return score

    def add_results_subgraph(self, statement=None, score=None, id_criterion=None):
        """
        Adds new subgraphs. This method complements the overwrite_graph method.
        :param statement:
        :param score:
        :param id_criterion:
        :return:
        """
        # Score
        score_uri = URIRef(CAMSSA + str(uuid.uuid4()), CAMSSA)
        #score_uri = URIRef(CAMSSA + id_score, CAMSSA) if id_score else URIRef(CAMSSA + str(uuid.uuid4()), CAMSSA)
        self.g.add((score_uri, RDF.type, CAV.Score))
        self.g.add((score_uri, RDF.type, OWL.NamedIndividual))
        self.g.add((score_uri, CAV.value, Literal(self.match_scoring(score) if not None else "None", datatype=XSD.int)))
        self.g.add((score_uri, CAV.assignedTo, URIRef(SC + 'c-' + id_criterion, SC)))
        # Statement
        statement_uri = URIRef(CAMSSA + str(uuid.uuid4()), CAMSSA)
        self.g.add((statement_uri, RDF.type, CAV.Statement))
        self.g.add((statement_uri, RDF.type, OWL.NamedIndividual))
        self.g.add((statement_uri, CAV.refersTo, score_uri))
        self.g.add((statement_uri, CAV.judgement, Literal(statement if not None else "None", lang='en')))
        # Assessment
        ass_uri = URIRef(CAMSSA + self.id_ass, CAMSSA)
        self.g.add((ass_uri, CAV.resultsIn, statement_uri))
        return

    def remove_subgraph(self, triple):
        """
        Removes either a subgraph contained in an assessment graph, or an assessment graph from the assessments graph.
        :param triple:
        :return:
        """
        self.g.remove(triple)
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

    def overwrite_graph(self, ass_id: str = None):
        """
        Overwrites certain content of the individual assessment graphs or the assessments graph.
        :param ass_id:
        :return: the larger graph resulting from the merging
        """
        # assessment identifier
        id_ass = self.id_ass if ass_id is None else ass_id
        # modify the scenario version identifier
        self.g.set((URIRef(CAMSSA + id_ass, CAMSSA), CAV.contextualisedBy, URIRef(SC + self.sc510_id, SC)))
        # id_spec = str(self.g.value(subject=URIRef(CAMSSA + str(id_ass).split("/")[-1]), predicate=CAMSS.assesses, any=False)).split(
        #    "/")[-1]
        # modify dates
        self.g.set((URIRef(CAMSSA + id_ass, CAMSSA), CAMSS.assessmentDate, Literal(None, datatype=URIRef(XSD.date))))
        self.g.set((URIRef(CAMSSA + id_ass, CAMSSA), CAMSS.submissionDate, Literal(None, datatype=URIRef(XSD.date))))
        # modify the CAMSS EIF scenario version
        self.g.set((URIRef(CAMSSA + id_ass, CAMSSA), CAMSS.toolVersion, URIRef(TOOL + "5.1.0", TOOL)))
        #
        # s stands for subject, p stands for predicate, o stands for object
        for s, p, o in self.g.triples((URIRef(CAMSSA + id_ass, CAMSSA), CAV.resultsIn, None)):
            # original statement for a specific criterion (old CAMSS EIF scenario)
            statement = self.g.value(subject=o, predicate=CAV.judgement, any=None)
            # original identifier of the criterion score (old CAMSS EIF scenario)
            id_score = str(self.g.value(subject=o, predicate=CAV.refersTo, any=None)).split("/")[-1]
            # original criterion score (old CAMSS EIF scenario)
            score = self.g.value(subject=URIRef(CAMSSA + id_score, CAMSSA), predicate=CAV.value, any=None)
            # original identifier of the criterion (old CAMSS EIF scenario)
            id_criterion = str(self.g.value(subject=URIRef(CAMSSA + str(id_score), CAMSSA), predicate=CAV.assignedTo,
                                            any=None)).split("/")[-1].split("c-")[-1]
            # remove sub_graph
            self.remove_subgraph((s, p, o))
            self.remove_subgraph((o, None, None))
            self.remove_subgraph((URIRef(CAMSSA + id_score, CAMSSA), None, None))
            # create sub_graph
            # id_score is maintained
            #
            duplicated_id_criterion = [i for i, x in enumerate(self.dict_crit[self.eif_version]) if
                                       x == id_criterion]

            if id_criterion in self.dict_crit[self.eif_version] and len(duplicated_id_criterion) > 1:
                while len(duplicated_id_criterion) > 0:
                    # equivalent identifier of the criterion
                    equiv_id_criterion = self.dict_crit[self.sc510_id][duplicated_id_criterion.pop()]
                    self.add_results_subgraph(statement, score, equiv_id_criterion)
            elif id_criterion in self.dict_crit[self.eif_version]:
                # equivalent identifier of the criterion
                equiv_id_criterion = self.dict_crit[self.sc510_id][self.dict_crit[self.eif_version].index(id_criterion)]
                self.add_results_subgraph(statement, score, equiv_id_criterion)
        # generate the list of unfilled criteria that need to be created
        unfilled_criteria = [i for i, x in enumerate(self.dict_crit[self.eif_version]) if
                             x == '']
        for index in unfilled_criteria:
            self.add_results_subgraph(id_criterion=self.dict_crit[self.sc510_id][index])
        self.g.bind('pcamss', CAMSS, replace=True, override=True)
        return self.g


# main function
# graph constructors inicialise here
if __name__ == '__main__':
    # input folder of the individual assessment graphs and the assessments graph
    input_folder = 'arti/in'
    # output folder of all updated graphs
    os.makedirs('arti/out/', exist_ok=True)
    # assessment graph constructor
    #final_ass_graph = GraphInstance(glob.glob(input_folder + '/AssessmentsG' + '/*')[0])
    # list of individual assessment files
    list_ass_names = [path for path in glob.iglob(input_folder + '/**', recursive=False) if
                      path != input_folder + "/AssessmentsG"]
    list_ass = []
    # this loop works on all individual assessment files (ttl files of the individual assessment graphs and assessments graph)
    for path in list_ass_names:
        # name of the file
        head = path[:-4].split("/")[-1]
        # output folder of the updated individual assessment graph
        new_dir = 'arti/out/' + head + f'/'
        os.makedirs(new_dir, exist_ok=True)
        # individual assessment graph constructor
        # CAMSS EIF scenario version of the working graph
        # assessment graph identifier
        new_graph = GraphInstance(path)
        new_graph.set_id_ass()
        new_graph.set_eif_version()
        # updating of the individual assessment graph and the assessments graph
        new_graph.overwrite_graph()
        #final_ass_graph.overwrite_graph(new_graph.id_ass)
        # serialisation of the updated individual assessment graph
        new_graph.serialize()
    final_ass_graph = GraphInstance(glob.glob(input_folder + '/AssessmentsG' + '/*')[0])
    for ass in list_ass:
        final_ass_graph.overwrite_graph(ass.id_ass)

    # output folder of the assessments graph
    # serialisation of the updated assessments graph
    final_ass_graph.serialize()
