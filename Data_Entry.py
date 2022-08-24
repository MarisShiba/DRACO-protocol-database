import google_auth_httplib2
import httplib2
import pandas as pd
import numpy as np
import ast
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import HttpRequest

st.title("DRACO Cell Culture Database")


SCOPE = "https://www.googleapis.com/auth/spreadsheets"
SPREADSHEET_ID = "1l5brTfIYWnQk0tm2PRaf7EKlX3GGSSIiqzs1RkWFdhY"
code_names = ['Carla', 'Pranav', 'Aayush', 'Janus']

# @st.experimental_singleton()
def connect_to_gsheet():
    # Create a connection object.
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[SCOPE],
    )

    # Create a new Http() object for every request
    def build_request(http, *args, **kwargs):
        new_http = google_auth_httplib2.AuthorizedHttp(
            credentials, http=httplib2.Http()
        )
        return HttpRequest(new_http, *args, **kwargs)

    authorized_http = google_auth_httplib2.AuthorizedHttp(
        credentials, http=httplib2.Http()
    )
    service = build(
        "sheets",
        "v4",
        requestBuilder=build_request,
        http=authorized_http,
    )
    gsheet_connector = service.spreadsheets()
    return gsheet_connector


def get_data(gsheet_connector, SHEET_NAME) -> pd.DataFrame:
    values = (
        gsheet_connector.values()
        .get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A:T",
        )
        .execute()
    )

    df = pd.DataFrame(values["values"])
    df.columns = df.iloc[0]
    df = df.loc[~df.Recorder.isin(code_names)]
    df = df[1:]
    return df

def display_paper_info(df, index):
    st.markdown("#### Title")
    st.markdown(f"### {str(df.at[index,'Title'])}")

    # st.markdown("#### Year")
    # st.write(str(df.at[index,'Publish date']))
    try:
        paper_types = ast.literal_eval(df.at[index, 'Type of paper'])
    except:
        paper_types = ["Not available"]
    # st.markdown("#### Type of paper")
    # st.write(", ".join(paper_types))

    col1, col2 = st.columns(2)
    col1.metric("Year", str(df.at[index,'Publish date']))
    col2.metric("Type of paper", ", ".join(paper_types))

    st.markdown("#### DOI/Link")
    st.write(str(df.at[index,'DOI']))
    st.write(str(df.at[index,'Link']))

    if len(str(df.at[index,'Abstract'])) > 0:
        st.markdown("### Abstract")
        st.write(str(df.at[index,'Abstract']))

def update_gsheet(gsheet_connector, SHEET_NAME, range, value) -> None:
    gsheet_connector.values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!{range}",
        body=dict(values=value),
        valueInputOption="USER_ENTERED",
    ).execute()

def add_row_to_gsheet(gsheet_connector, SHEET_NAME, row) -> None:
    gsheet_connector.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A:T",
        body=dict(values=row),
        valueInputOption="USER_ENTERED",
    ).execute()

gsheet_connector = connect_to_gsheet()
df = get_data(gsheet_connector, 'API_results')
cols = st.columns((1, 1, 1))

paper_idx = st.number_input("Desired paper index:", value=-99)
if paper_idx != -99 and paper_idx > 0:
    i = paper_idx
else:
    i = df.index.values[0]

# show_paper = st.button("Show paper information")
show_paper = st.checkbox("Show paper information")
stop_submit = False

if show_paper:
    if paper_idx == -99 or paper_idx < 0:
        st.warning("The chosen paper index is invalid, thus the first paper is chosen.")
    try:
        display_paper_info(df, i)
    except:
        stop_submit = True
        st.error("The given index is not valid!")
else:
    stop_submit = True

form = st.form(key="annotation")

with form:
    industry = st.text_input("Industry:")
    cols = st.columns((1, 1))
    cell_type = cols[0].text_input("Type of cells:")
    culture_type = cols[1].text_input("Type of culture:")

    cols = st.columns((1, 1))
    scaffold = cols[0].text_input("Scaffold:")
    media = cols[1].text_input("Media:")

    culture_sys = st.text_input("Culturing system:")
    process = st.text_area("Process:")
    notes = st.text_area("Notes:")
    tested = st.checkbox('Tested by SLD')

    codeword = st.text_area("Code word:")
    submitted = st.form_submit_button(label="Submit")

if submitted:
    if stop_submit:
        st.error("Submission is not possible since the paper index is invalid.")
    else:
        api_data = list(df.loc[[i]][['Title',
                                    'DOI',
                                    'Link',
                                    'Publish date',
                                    'Abstract',
                                    'Keywords',
                                    'Type of paper',
                                    'Authors',
                                    'Insitution']].values[0])
        if tested:
            tested = 'Yes'
        else:
            tested = 'No'
        if len(notes) == 0:
            notes = ""

        data_row = [industry, cell_type, culture_type,
                    scaffold, media, culture_sys, process]
        data_row_names = ['Industry', 'Cell type', 'Culture type',
                          'Scaffold', 'Media', 'Culture system', 'Process']
        empties = []
        for j in range(len(data_row)):
            if len(data_row[j]) == 0:
                st.warning(f"{data_row_names[j]} info is missing")
                empties.append(0)

        if len(empties) == len(data_row):
            st.error("No submission can be made with all fields empty.")
        else:
            data_row += [tested, notes]
            if codeword in code_names:
                add_row_to_gsheet(
                    gsheet_connector,
                    'Test_streamlit',
                    [api_data+[""]+data_row+[codeword]],
                )

                update_gsheet(gsheet_connector, 'API_results', f"T{i+1}:U{i+1}", [[codeword, '']])
                st.success("Thanks! Your data was recorded.")
            else:
                st.error("Wrong code name.")

expander = st.expander("See all records")
with expander:
    st.dataframe(get_data(gsheet_connector, 'API_results')[['Title', 'Publish date', 'Type of paper']])
