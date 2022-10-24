from rdflib import URIRef, Literal, Namespace, Graph, term
from rdflib.namespace import RDF, OWL, XSD
import os
import pandas as pd
import glob

CAMSS = Namespace("http://data.europa.eu/2sa#")
CAMSSA = Namespace("http://data.europa.eu/2sa/assessments/")
CAV = Namespace("http://data.europa.eu/2sa/cav#")
CSSV_RSC = Namespace("http://data.europa.eu/2sa/cssv/rsc/")
SC = Namespace("http://data.europa.eu/2sa/scenarios#")
SCHEMA = Namespace("http://schema.org/")
STATUS = Namespace("http://data.europa.eu/2sa/rsc/assessment-status#")
TOOL = Namespace("http://data.europa.eu/2sa/rsc/toolkit-version#")


def set_graph(file_path: str):
    """
    Reads a ttl file and transforms it to an rdflib graph instance.
    :param file_path:
    :return:
    """
    data = open(file_path, 'rb')
    g = Graph()
    g.parse(data, format='ttl')
    data.close()
    return g

def get_ass_scores(g: Graph):
    sparql_query = f"""
        SELECT ?score_id ?score
        WHERE {{
        ?score_id cav:value ?score .
        }}
        """
    return [int(stmt[1].value) for stmt in g.query(sparql_query)]

def get_score_from_criterionA2(g: Graph, criterion_id: str):
    uri_ass = g.value(predicate=RDF.type, object=CAV.Assessment, any=None)
    uri_criterion = SC + 'c-' + criterion_id

    sparql_query = f"""
        SELECT ?score_id ?score
        WHERE {{
        ?score_id cav:assignedTo <{uri_criterion}>;
            cav:value ?score .
        }}
        """

    # results = g.query(sparql_query)
    # list_scores = [int(stmt[1].value) for stmt in results]
    # return list_scores

    '''
    The line below iterates every row returned by the query, converts the score Literal to an integer and collects this value in a list.
    This list is used for calculating the assessments scores.
    '''
    return [int(stmt[1].value) for stmt in g.query(sparql_query)][0]

def read_files():
    list_ass_names = [path for path in glob.iglob('arti/out/**/**', recursive=False) if
                      path != '/arti/out/CAMSS_Assessments_graph']

    with open(list_ass_names[0], 'r') as f:
        for line in f.readlines():
            print(line, end='')

def get_punct (responses: dict):
    os.makedirs('arti/punct/', exist_ok=True)
    df = pd.DataFrame().from_dict(responses, columns=['old AUT score (%)', 'old STRENG score (%)', 'new AUT score (%)', 'new STRENG score (%)'], orient='index')
    df.columns = ['old AUT score (%)', 'old STRENG score (%)', 'new AUT score (%)', 'new STRENG score (%)']
    df = df[['old AUT score (%)', 'new AUT score (%)', 'old STRENG score (%)', 'new STRENG score (%)']]
    df.to_csv(f'arti/punct/EIFScenario510-scoresComparation.csv')

def read_punct():
    df = pd.read_csv('arti/punct/EIFScenario510-scoresComparation.csv')
    df.rename(columns={'Unnamed: 0': 'Specification'}, inplace=True)
    return df

#print(get_ass_scores(set_graph('test_in.ttl')))