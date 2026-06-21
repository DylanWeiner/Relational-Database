import sqlite3
import pandas as pd
import streamlit as st
import pandas as pd
from scipy.stats import mannwhitneyu
import plotly.express as px


def MakeDashboard():
    st.set_page_config(
        page_title="Cell Relational Database",
        layout="wide"
    ) # Loosely formats the database application
    connection = st.connection("cell_database", type="sql") # Connects to database by calling our secrets.toml file
    st.sidebar.header("Database Dashboard Filters") # Creates a Header for the Filter of the Database

    st.title("Cell Database")

    # population_df = connection.query("SELECT DISTINCT sample FROM immunePops;", ttl=3600) # Our time to live parameter will be an hour so we don't trigger the rerun rule anytime we interact with the page
    # population_list = population_df["sample"].tolist()
    # current_population = st.sidebar.selectbox("Population Selection", options=population_list)

    # condition_df = connection.query("SELECT DISTINCT sample FROM conditionDeets;", ttl=3600)
    # condition_list = condition_df["sample"].tolist()
    # current_condition = st.sidebar.selectbox("Condition Selection", options=condition_list)

    df_data_overview = connection.query(
        "SELECT * FROM initialAnalysis;",
        # params={"population_param": current_population, "condition_param": current_condition},
        ttl=300
    )

    df_stat_analysis = connection.query(
        "SELECT * FROM statisticalAnalysis;",
        # params={"population_param": current_population, "condition_param": current_condition},
        ttl=300
    )

    # df_stat_analysis_full = connection.query(
    #     "SELECT * FROM statisticalAnalysisFull;",
    #     params={"population_param": current_population, "condition_param": current_condition},
    #     ttl=300
    # )
    sql = """
        SELECT subject, time_from_treatment, sample_percentage, response
        FROM statisticalAnalysis
        WHERE treatment = :treatment_param
        AND condition = :condition_param
        AND sample_type = :sample_type_param
        ORDER BY subject, time_from_treatment;
    """

    df_full_data = connection.query(
        "SELECT * FROM immunePops NATURAL JOIN conditionDeets NATURAL JOIN sampleMetadata",
        # params={"population_param": current_population, "condition_param": current_condition},
        ttl=300
    )

    if df_data_overview.empty:
        st.warning("This filter combination does not exist!")
    else:
        st.header("Initial Analysis")
        st.dataframe(df_data_overview, use_container_width=True, hide_index=True,)
        st.dataframe(df_full_data, use_container_width=True, hide_index=True)
    
    if df_stat_analysis.empty:
        st.warning("Statistical Analysis's filter combination does not exist!")
    else:
        st.header("Statistical Analysis")
        st.dataframe(df_stat_analysis, use_container_width=True, hide_index=True,)
        # st.dataframe(df_stat_analysis_full, use_container_width=True, hide_index=True,)


def MakeInitAnalysis(connCur):
    connCur.execute("SELECT name FROM sqlite_master WHERE type='table' and name=?", ('initialAnalysis',)) # This checks if the table this script is implementing already exists within our database
    if(connCur.fetchone()):
        connCur.execute("DROP TABLE initialAnalysis") # Deletes table each time this app is run
    
    connCur.execute("""
        CREATE TABLE initialAnalysis (
            sample VARCHAR,
            colony_type VARCHAR,
            sample_count INTEGER,
            sample_percentage REAL,
            PRIMARY KEY (sample, colony_type)
            CONSTRAINT sample_ref
                FOREIGN KEY (sample)
                REFERENCES immunePops(sample)
        )
        """) # Created a table containing the sample name, sample type, sample type total, and sample percentage.
    
    connCur.execute("""
        WITH sampleSum AS(SELECT sample, (b_cell+cd8_t_cell+cd4_t_cell+nk_cell+monocyte) AS total_count FROM immunePops GROUP BY sample)
        INSERT INTO initialAnalysis(sample, colony_type, sample_count, sample_percentage)
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


def MakeStatAnalysis(connCur):
    connCur.execute("SELECT name FROM sqlite_master WHERE type='table' and name=?", ('statisticalAnalysis',)) # This checks if the table this script is implementing already exists within our database
    if(connCur.fetchone()):
        connCur.execute("DROP TABLE statisticalAnalysis") # Deletes table each time this app is run

    connCur.execute("""
        CREATE TABLE statisticalAnalysis (
            sample VARCHAR,
            sample_type VARCHAR,
            colony_type VARCHAR,
            sample_count INTEGER,
            sample_percentage REAL,
            treatment VARCHAR,
            condition VARCHAR,
            response VARCHAR,
            time_from_treatment_start INTEGER,
            subject VARCHAR,
            PRIMARY KEY (sample, colony_type)
            CONSTRAINT sample_ref
                FOREIGN KEY (sample)
                REFERENCES immunePops(sample)
        )
        """) # Create a table to hold the info for Part 3 of Bob's insatiable curiosity.

    # connCur.execute("""
    #                 WITH allResponses AS
    #                 (SELECT sample, sample_type, colony_type, sample_count, sample_percentage, treatment, condition, response
    #                     FROM conditionDeets NATURAL JOIN initialAnalysis NATURAL JOIN sampleMetadata)
    #                 INSERT INTO statisticalAnalysis(sample, sample_type, colony_type, sample_count, sample_percentage, treatment, condition, response)
    #                 SELECT sample, sample_type, colony_type, sample_count, sample_percentage, treatment, condition, response
    #                     FROM allResponses;
    #                 """) # Inserts values into the table where treatment was miraclib, the patient had melanoma
    connCur.execute("""
                    WITH allResponses AS
                    (SELECT sample, sample_type, colony_type, sample_count, sample_percentage, treatment, time_from_treatment_start, subject, condition, response
                        FROM conditionDeets NATURAL JOIN initialAnalysis NATURAL JOIN sampleMetadata)
                    INSERT INTO statisticalAnalysis(sample, sample_type, colony_type, sample_count, sample_percentage, treatment, time_from_treatment_start, subject, condition, response)
                    SELECT sample, sample_type, colony_type, sample_count, sample_percentage, treatment, time_from_treatment_start, subject, condition, response
                        FROM allResponses;
                    """) # Inserts values into the table for all Responses for sorting


# def MakeStatComparison(connCur):
#     connCur.execute("SELECT name FROM sqlite_master WHERE type='table' and name=?", ('statisticalAnalysisFull',)) # This checks if the table this script is implementing already exists within our database
#     if(connCur.fetchone()):
#         connCur.execute("DROP TABLE statisticalAnalysisFull") # Deletes table each time this app is run

#     connCur.execute("""
#             CREATE TABLE statisticalAnalysisFull (
#                 sample_percentage REAL,
#                 treatment VARCHAR,
#                 condition VARCHAR,
#                 response VARCHAR,
#                 time_from_treatment_start INTEGER,
#                 subject VARCHAR,
#                 PRIMARY KEY (subject, time_from_treatment_start)
#                 CONSTRAINT sample_ref
#                     FOREIGN KEY (subject)
#                     REFERENCES sampleMetadata(subject),
#                 CONSTRAINT condition_ref
#                     FOREIGN KEY (time_from_treatment_start)
#                     REFERENCES conditionDeets(time_from_treatment_start)
#             )
#             """)
    
#     connCur.execute("""
#                     WITH statPulls AS
#                     (SELECT treatment, subject, time_from_treatment_start, sample_percentage, response
#                     FROM statisticalAnalysis
#                     WHERE treatment = :treatment_param
#                     AND condition = :condition_param
#                     AND sample_type = :sample_type_param
#                     AND response = :response
#                     ORDER BY subject, time_from_treatment_start)
#                     INSERT INTO statisticalAnalysisFull(treatment, subject, time_from_treatment_start, sample_percentage, response)
#                     SELECT treatment, subject, time_from_treatment_start, sample_percentage, response FROM statPulls;
#                     """)


def renderComparisonSection():
    connection = st.connection("cell_database", type="sql")
    statAnalysis = connection.query("SELECT * FROM statisticalAnalysis", ttl=300)

    condition_options = statAnalysis["condition"].unique().tolist()
    treatment_options = statAnalysis["treatment"].unique().tolist()
    sample_options = statAnalysis["sample_type"].unique().tolist()

    selected_condition = st.selectbox(
        "Condition:", options=condition_options,
        index=condition_options.index("melanoma")
    )
    selected_treatment = st.selectbox(
        "Treatment:", options=treatment_options,
        index=treatment_options.index("miraclib")
    )
    selected_sample = st.selectbox(
        "Sample type:", options=sample_options,
        index=sample_options.index("PBMC")
    )

    # Filter on sample_type (PBMC) — colony_type is left untouched
    # so every cell population stays in the result
    query = """
        SELECT subject, colony_type, sample_percentage, response
        FROM statisticalAnalysis
        WHERE condition = :condition_param
          AND treatment = :treatment_param
          AND sample_type = :sample_param
    """
    df_allStats = connection.query(
        query,
        params={
            "condition_param": selected_condition,
            "treatment_param": selected_treatment,
            "sample_param": selected_sample
        },
        ttl=300
    )

    if df_allStats.empty:
        st.warning("No data matches this combination.")
        return

    # Boxplot, one panel per cell population
    fig = px.box(
        df_allStats, x="response", y="sample_percentage", color="response",
        facet_col="colony_type",
        title="Relative Frequency by Response Status, per Cell Population"
    )
    st.plotly_chart(fig, use_container_width=True)

    # Significance test, per cell population
    results = []
    for population in df_allStats["colony_type"].unique():
        subset = df_allStats[df_allStats["colony_type"] == population]
        responders = subset[subset["response"] == "yes"]["sample_percentage"]
        non_responders = subset[subset["response"] == "no"]["sample_percentage"]

        if len(responders) < 2 or len(non_responders) < 2:
            continue

        stat, p_value = mannwhitneyu(responders, non_responders, alternative="two-sided")
        results.append({
            "colony_type": population,
            "responder_median": responders.median(),
            "non_responder_median": non_responders.median(),
            "p_value": p_value
        })

    results_df = pd.DataFrame(results)
    if not results_df.empty:
        results_df["significant"] = results_df["p_value"] < 0.05
        st.dataframe(results_df, use_container_width=True, hide_index=True)
    significant_populations = results_df[results_df["significant"]]["colony_type"].tolist()

    if significant_populations:
        st.success(f"Significant difference found in: {', '.join(significant_populations)} "
                f"(p < 0.05), suggesting these populations may help predict response to {selected_treatment}.")
    else:
        st.info("No cell populations showed a statistically significant difference "
                "between responders and non-responders at p < 0.05.")


def renderBaselineSummary():
    connection = st.connection("cell_database", type="sql")
    statAnalysis = connection.query("SELECT * FROM statisticalAnalysis", ttl=300)

    condition_options = statAnalysis["condition"].unique().tolist()
    treatment_options = statAnalysis["treatment"].unique().tolist()
    sample_options = statAnalysis["sample_type"].unique().tolist()
    time_options = sorted(statAnalysis["time_from_treatment_start"].unique().tolist())

    selected_condition = st.selectbox(
        "Condition:", options=condition_options,
        index=condition_options.index("melanoma")
    )
    selected_treatment = st.selectbox(
        "Treatment:", options=treatment_options,
        index=treatment_options.index("miraclib")
    )
    selected_sample = st.selectbox(
        "Sample type:", options=sample_options,
        index=sample_options.index("PBMC")
    )
    selected_time = st.selectbox(
        "Time from treatment start:", options=time_options,
        index=time_options.index(0)
    )

    base_cte = """
        WITH baseline AS (
            SELECT DISTINCT sample, subject, project, response, sex
            FROM initialAnalysis
            NATURAL JOIN sampleMetadata
            NATURAL JOIN conditionDeets
            WHERE condition = :condition_param
              AND sample_type = :sample_param
              AND treatment = :treatment_param
              AND time_from_treatment_start = :time_param
        )
    """
    params = {
        "condition_param": selected_condition,
        "sample_param": selected_sample,
        "treatment_param": selected_treatment,
        "time_param": selected_time
    }

    by_project = connection.query(base_cte + "SELECT project, COUNT(*) AS sample_count FROM baseline GROUP BY project;", params=params, ttl=300)
    by_response = connection.query(base_cte + "SELECT response, COUNT(DISTINCT subject) AS subject_count FROM baseline GROUP BY response;", params=params, ttl=300)
    by_sex = connection.query(base_cte + "SELECT sex, COUNT(DISTINCT subject) AS subject_count FROM baseline GROUP BY sex;", params=params, ttl=300)

    if by_project.empty and by_response.empty and by_sex.empty:
        st.warning("No data matches this combination.")
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Samples by Project")
        fig1 = px.bar(by_project, x="project", y="sample_count")
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.subheader("Subjects by Response")
        fig2 = px.bar(by_response, x="response", y="subject_count", color="response")
        st.plotly_chart(fig2, use_container_width=True)

    with col3:
        st.subheader("Subjects by Sex")
        fig3 = px.bar(by_sex, x="sex", y="subject_count", color="sex")
        st.plotly_chart(fig3, use_container_width=True)


def main():
    connection = sqlite3.connect("cell-database.db")
    connCur = connection.cursor()
    MakeInitAnalysis(connCur) # Part 1's table construction
    MakeStatAnalysis(connCur) # Part 2's table construction
    MakeDashboard() # Construction of the streamlit dashboard
    renderComparisonSection() # Part 3's graph and table construction
    renderBaselineSummary()
    connection.commit()
    connection.close()

if __name__ == "__main__":
    main()