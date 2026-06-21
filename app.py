import sqlite3
import pandas as pd
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

def MakeDashboard():
    st.set_page_config(
        page_title="Cell Relational Database",
        layout="wide"
    ) # Loosely formats the database application
    connection = st.connection("cell_database", type="sql") # Connects to database by calling our secrets.toml file
    st.sidebar.header("Database Dashboard Filters") # Creates a Header for the Filter of the Database

    # st.title("Cell Database")

    population_df = connection.query("SELECT DISTINCT sample FROM immunePops;", ttl=3600) # Our time to live parameter will be an hour so we don't trigger the rerun rule anytime we interact with the page
    population_list = population_df["sample"].tolist()
    current_population = st.sidebar.selectbox("Population Selection", options=population_list)

    condition_df = connection.query("SELECT DISTINCT sample FROM conditionDeets;", ttl=3600)
    condition_list = condition_df["sample"].tolist()
    current_condition = st.sidebar.selectbox("Condition Selection", options=condition_list)

    main_query = """
        SELECT * FROM statisticalAnalysis;
    """
    df = connection.query(
        main_query,
        params={"population_param": current_population, "condition_param": current_condition},
        ttl=300
    )

    full_data = connection.query(
        "SELECT * FROM immunePops NATURAL JOIN conditionDeets NATURAL JOIN sampleMetadata",
        params={"population_param": current_population, "condition_param": current_condition},
        ttl=300
    )

    if df.empty:
        st.warning("This filter combination does not exist!")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.dataframe(full_data, use_container_width=True, hide_index=True)


def MakeAnalysis():
    connection = sqlite3.connect("cell-database.db")
    connCur = connection.cursor()
    connCur.execute("SELECT name FROM sqlite_master WHERE type='table' and name=?", ('statisticalAnalysis',)) # This checks if the table this script is implementing already exists within our database
    if(connCur.fetchone()):
        connCur.execute("DROP TABLE statisticalAnalysis") # Deletes table each time this app is run
    
    connCur.execute("""
        CREATE TABLE statisticalAnalysis (
            sample VARCHAR,
            sample_type VARCHAR,
            sample_count INTEGER,
            sample_percentage REAL,
            FOREIGN KEY (sample) REFERENCES immunePops(sample)
        )
        """) # Created a table containing the sample name, sample type, sample type total, and sample percentage.
    
    connCur.execute("""
        WITH sampleSum AS(SELECT sample, (b_cell+cd8_t_cell+cd4_t_cell+nk_cell+monocyte) AS total_count FROM immunePops GROUP BY sample)
        INSERT INTO statisticalAnalysis(sample, sample_type, sample_count, sample_percentage)
        SELECT sample, 'b_cell', b_cell, ROUND(100.0 * b_cell/ total_count, 2) FROM immunePops NATURAL JOIN sampleSum
        UNION ALL
        SELECT sample, 'cd8_t_cell', cd8_t_cell, ROUND(100.0 * cd8_t_cell/ total_count, 2) FROM immunePops NATURAL JOIN sampleSum
        UNION ALL
        SELECT sample, 'cd4_t_cell', cd4_t_cell, ROUND(100.0 * cd4_t_cell/ total_count, 2) FROM immunePops NATURAL JOIN sampleSum
        UNION ALL
        SELECT sample, 'nk_cell', nk_cell, ROUND(100.0 * nk_cell/ total_count, 2) FROM immunePops NATURAL JOIN sampleSum
        UNION ALL
        SELECT sample, 'monocyte', monocyte, ROUND(100.0 * monocyte/ total_count, 2) FROM immunePops NATURAL JOIN sampleSum ORDER BY sample;
    """) # Inserts sample information for each type, percentage is a decimal to trigger floating point division, and rounded to the two nearest sig figs
        # Order By groups everything by sample name rather than sample type

    summary_df = pd.read_sql_query("SELECT * FROM statisticalAnalysis;", connection) # We use read sql query since we get output
    print(summary_df)
    connection.commit()
    connection.close()


def MakeDataOverview():
    connection = st.connection("cell_database", type="sql")
    # connCur = connection.cursor()

    population_df = connection.query("SELECT DISTINCT sample FROM immunePops;", ttl=3600) # Our time to live parameter will be an hour so we don't trigger the rerun rule anytime we interact with the page
    population_list = population_df["sample"].tolist()
    current_population = st.sidebar.selectbox("Population Selection", options=population_list)

    condition_df = connection.query("SELECT DISTINCT sample FROM conditionDeets;", ttl=3600)
    condition_list = condition_df["sample"].tolist()
    current_condition = st.sidebar.selectbox("Condition Selection", options=condition_list)

    data_table = pd.read_sql_query("""
                    WITH allResponses AS(SELECT sample, sample_type, sample_count, sample_percentage, treatment, condition FROM statisticalAnalysis NATURAL JOIN conditionDeets NATURAL JOIN sampleMetadata WHERE treatment='miraclib' AND condition='melanoma' AND sample_type='PBMC'),
                    posiResponse AS(SELECT sample, sample_type, sample_count, sample_percentage FROM allResponses WHERE response='yes'),
                    negResponses AS(SELECT sample, sample_type, sample_count, sample_percentage FROM allResponses WHERE response='no')
                    SELECT * FROM allResponses;
                    """, connection) # This checks if the table this script is implementing already exists within our database

    data_overview = connection.query(
        data_table,
        params={"population_param": current_population, "condition_param": current_condition},
        ttl=300
    )

    if data_overview.empty:
        st.warning("This filter combination does not exist!")
    else:
        st.dataframe(data_overview, use_container_width=True, hide_index=True)

    connection.commit()
    connection.close()

def main():
    MakeAnalysis()
    MakeDashboard()
    MakeDataOverview()

if __name__ == "__main__":
    main()