import os
import re
import pandas as pd
import glob


def set_name(file_path: str):
    """
    Sets the specification's name from the original file.
    :param file_path: filepath of the RDF file
    :return: a shortened name for the assessment's name
    """
    # name format of EIF 300 and 310 scenarios
    pattern1 = re.compile(
        r'CAMSS[\s\-\_]Assessment(\_?EIF\sScenario-?)?[\s\-\_](of[\s\-\_])?(.+?)(\_?EIF\s?Scenario\_?)?\_?v\.?1')
    pattern2 = re.compile(r'EIF-5\.0\.0-CAMSSAssessment[\s\-\_](.+)$')
    # name format of EIF
    pattern3 = re.compile(r'CAMSS[\_\-\s]Ontology')
    # search for patterns
    name = file_path.strip()
    name1 = pattern1.search(name)
    name2 = pattern2.search(name)
    name3 = pattern3.search(name)
    if name1:
        return name1.group(3)
    elif name2:
        return name2.group(1)
    elif name3:
        return 'CAMSS_Assessments_graph'
    else:
        return name

def read_files():
    """
    (Jupyter Notebook) Reads an arbitraty RDF file after the migration.
    """
    list_ass_names = [path for path in glob.iglob('arti/out/**', recursive=False) if
                      path != 'arti/out/CAMSS_Assessments_graph']

    with open(list_ass_names[0], 'r') as f:
        for line in f.readlines():
            print(line, end='')

def read_assessments_graph():
    """
    (Jupyter Notebook) Reads the CAMSS Assessments graph RDF file after the migration.
    """
    path = 'arti/out/CAMSS_Assessments_graph/CAMSS_Assessments_graph.ttl'
    with open(path, 'r') as f:
        for line in f.readlines():
            print(line, end='')

def get_punct (responses: dict, gradients: dict):
    """
    Provides a table of the migration results.
    :param responses: old and new scores after the migration per assessment
    :param gradients: number of not applicable, negative and positive answers per assessment
    """
    os.makedirs('arti/punct/', exist_ok=True)
    df = pd.DataFrame().from_dict(responses, columns=['old AUT score (%)', 'old STRENG score (%)', 'new AUT score (%)', 'new STRENG score (%)', 'Previous EIF'], orient='index')
    df.columns = ['old AUT score (%)', 'old STRENG score (%)', 'new AUT score (%)', 'new STRENG score (%)', 'Previous EIF']
    df2 = pd.DataFrame().from_dict(gradients, columns=['Not Answer (#)', 'Not Applicable (#)', 'No/Gradient', 'Yes/Gradient (#)'], orient='index')
    df = df[['Previous EIF', 'old AUT score (%)', 'new AUT score (%)', 'old STRENG score (%)', 'new STRENG score (%)']]
    df = df.join(df2)
    df.to_csv(f'arti/punct/EIFScenario510-scoresComparison.csv')

def read_punct():
    """
    (Jupyter Notebook) Reads the table of the migration results.
    :return: such table
    """
    df = pd.read_csv('arti/punct/EIFScenario510-scoresComparison.csv')
    df.rename(columns={'Unnamed: 0': 'Specification'}, inplace=True)
    pd.options.display.max_rows = None
    return df
