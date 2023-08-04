import os
import re
import pandas as pd
import glob
from IPython.core.display import display, HTML
from IPython.display import Javascript, display
import ipywidgets as widgets


def set_name(file_path: str):
    """
    Sets the specification's name from the original file.
    :param file_path: filepath of the RDF file
    :return: a shortened name for the assessment's name
    """
    # name format of EIF 300 and 310 scenarios
    # pattern1 = re.compile(
    #     r'CAMSS[\s\-\_]Assessment(\_?EIF\sScenario-?)?[\s\-\_](of[\s\-\_])?(.+?)(\_?EIF\s?Scenario\_?)?\_?v\.?1')
    #pattern2 = re.compile(r'EIF-5\.0\.0-CAMSSAssessment[\s\-\_](.+)$')
    pattern2 = re.compile(r'EIF-5\.1\.0-CAMSSAssessment[\s\-\_](.+)$')
    # name format of EIF
    pattern3 = re.compile(r'CAMSS[\_\-\s]Ontology')
    # search for patterns
    print(file_path)
    name = file_path.strip()
    # name1 = pattern1.search(name)
    # name2 = pattern2.search(name)
    name2 = pattern2.search(name)
    name3 = pattern3.search(name)
    # if name1:
    #     return name1.group(3)
    # elif name2:
    #     return name2.group(1)
    if name2:
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
    #df = pd.read_csv('arti/punct/EIFScenario510-scoresComparison.csv')
    df = pd.read_excel('arti/punct/EIFScenario510-scoresComparation.xlsx')
    df.rename(columns={'Unnamed: 0': 'Specification'}, inplace=True)
    pd.options.display.max_rows = None
    return df

###########################################
############ Hide code ####################
###########################################

# source: https://www.titanwolf.org/Network/q/8f9729f8-fc73-4bc7-97b8-dcb9604a9356/y

javascript_functions = {False: "hide()", True: "show()"}
button_descriptions  = {False: "Show code", True: "Hide code"}


def toggle_code(state):

    """
    Toggles the JavaScript show()/hide() function on the div.input element.
    """

    output_string = "<script>$(\"div.input\").{}</script>"
    output_args   = (javascript_functions[state],)
    output        = output_string.format(*output_args)

    display(HTML(output))


def button_action(value):

    """
    Calls the toggle_code function and updates the button description.
    """

    state = value.new

    toggle_code(state)

    value.owner.description = button_descriptions[state]

def display_hidebuttom():
    state = False
    toggle_code(state)

    button = widgets.ToggleButton(state, description = button_descriptions[state])
    button.observe(button_action, "value")

    display(button)