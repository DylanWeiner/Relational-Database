import sqlite3
import pandas as pd
import streamlit as st
import pandas as pd
from scipy.stats import mannwhitneyu
import plotly.express as px


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

    connCur.execute("""
                    WITH allResponses AS
                    (SELECT sample, sample_type, colony_type, sample_count, sample_percentage, treatment, time_from_treatment_start, subject, condition, response
                        FROM conditionDeets NATURAL JOIN initialAnalysis NATURAL JOIN sampleMetadata)
                    INSERT INTO statisticalAnalysis(sample, sample_type, colony_type, sample_count, sample_percentage, treatment, time_from_treatment_start, subject, condition, response)
                    SELECT sample, sample_type, colony_type, sample_count, sample_percentage, treatment, time_from_treatment_start, subject, condition, response
                        FROM allResponses;
                    """) # Inserts values into the table for all Responses for sorting


def MakeDashboard():
    st.set_page_config(
        page_title="Cell Relational Database",
        layout="wide"
    ) # Loosely formats the database application
    connection = st.connection("cell_database", type="sql") # Connects to database by calling our secrets.toml file

    st.title("Cell Database")

    df_data_overview = connection.query(
        "SELECT * FROM initialAnalysis;",
        ttl=300
    ) # Creates the dataframe for our initial analysis

    if df_data_overview.empty:
        st.warning("This filter combination does not exist!")
    else:
        st.header("Initial Analysis")
        st.dataframe(df_data_overview, use_container_width=True, hide_index=True,) # This generates the physical
        # summary table we produced in our helper function for our initial table of each cell colony per sample.


def renderComparisonSection():
    connection = st.connection("cell_database", type="sql")
    statAnalysis = connection.query("SELECT * FROM statisticalAnalysis", ttl=300)

    condition_options = statAnalysis["condition"].unique().tolist() # These commands grab each distinct value
    treatment_options = statAnalysis["treatment"].unique().tolist() # in each of these lists and saves them to
    sample_options = statAnalysis["sample_type"].unique().tolist() # a list datatype

    st.header("Statistical Analysis") # Makes a header for our chart
    selected_condition = st.selectbox(
        "Condition:", options=condition_options,
        index=condition_options.index("melanoma")
    ) # This allows us to select our options for each dropdown menu from the existing cells in the relevant columns.
    selected_treatment = st.selectbox(
        "Treatment:", options=treatment_options,
        index=treatment_options.index("miraclib")
    ) # I set the menus to default to the query Bob was searching for since it simplifies the interactions necessary
    selected_sample = st.selectbox( # to obtain the desired results
        "Sample type:", options=sample_options,
        index=sample_options.index("PBMC")
    )

    dropdown_val_query = """
        SELECT subject, colony_type, sample_percentage, response
        FROM statisticalAnalysis
        WHERE condition = :condition_param
          AND treatment = :treatment_param
          AND sample_type = :sample_param
    """ # The param values are just the sqlalchemy placeholders that keep the spot filled before we define our
    # values properly
    df_allStats = connection.query(
        dropdown_val_query,
        params={
            "condition_param": selected_condition,
            "treatment_param": selected_treatment,
            "sample_param": selected_sample
        },
        ttl=300
    ) # This sets our placeholders to the relevant columns from our table

    if df_allStats.empty:
        st.warning("No data matches this combination.")
        return # This just throws a warning for an empty dataframe rather than printing the empty dataframe

    # Boxplot, one panel per cell population
    fig = px.box(
        df_allStats, x="response", y="sample_percentage", color="response",
        facet_col="colony_type", # Groups our boxplots by colony_type
        title="Relative Frequency by Response Status, per Cell Population"
    ) # We have one panel per colony type; each has its own yes and no box, and is colored by response
    st.plotly_chart(fig, use_container_width=True) # Places the boxplot on the page

    # Significance test, per cell population
    results = []
    for population in df_allStats["colony_type"].unique(): # We loop through every unique colony type
        subset = df_allStats[df_allStats["colony_type"] == population] # This saves only the rows where population is the relevant colony_type
        responders = subset[subset["response"] == "yes"]["sample_percentage"] 
        non_responders = subset[subset["response"] == "no"]["sample_percentage"] # Same thing with responses yes and no

        if len(responders) < 2 or len(non_responders) < 2:
            continue # We need at least two values for this statistical test so this is our catch for relevant edge cases

        stat, p_value = mannwhitneyu(responders, non_responders, alternative="two-sided") # Calls Mann-Whitney U Test (Looks for statistical difference btwn 2 independent groups)
        results.append({
            "colony_type": population,
            "responder_median": responders.median(),
            "non_responder_median": non_responders.median(),
            "p_value": p_value
        }) # Creates a dictionary for the relevant results for our colony types

    results_df = pd.DataFrame(results) # We then set our results to a dataframe
    if not results_df.empty: # This is where we create the column for significance and mark whether or not it is present
        results_df["significant"] = results_df["p_value"] < 0.05
        st.dataframe(results_df, use_container_width=True, hide_index=True)
        significant_populations = results_df[results_df["significant"]]["colony_type"].tolist()

    if significant_populations:
        st.success(f"Significant difference found in: {', '.join(significant_populations)} "
                f"(p < 0.05), suggesting these populations may help predict response to {selected_treatment}.")
    else:
        st.info("""No cell populations showed a statistically significant difference 
                between responders and non-responders at p < 0.05.""")
    # This is here to provide a readable answer to the user


def renderBaselineSummary():
    connection = st.connection("cell_database", type="sql")
    statAnalysis = connection.query("SELECT * FROM statisticalAnalysis", ttl=300)

    condition_options = statAnalysis["condition"].unique().tolist()
    treatment_options = statAnalysis["treatment"].unique().tolist()
    sample_options = statAnalysis["sample_type"].unique().tolist()
    time_options = sorted(statAnalysis["time_from_treatment_start"].unique().tolist())

    st.header("Subset Analyses")
    selected_condition = st.selectbox(
        "Condition:", options=condition_options,
        index=condition_options.index("melanoma"),
        key="baseline_condition"
    )
    selected_treatment = st.selectbox(
        "Treatment:", options=treatment_options,
        index=treatment_options.index("miraclib"),
        key="baseline_treatment"
    )
    selected_sample = st.selectbox(
        "Sample type:", options=sample_options,
        index=sample_options.index("PBMC"),
        key="baseline_sample"
    )
    selected_time = st.selectbox(
        "Time from treatment start:", options=time_options,
        index=time_options.index(0),
        key="baseline_time"
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


def renderDescriptiveStats():
    connection = st.connection("cell_database", type="sql")
    df = connection.query("SELECT * FROM statisticalAnalysis NATURAL JOIN sampleMetadata", ttl=300)

    gender_options = ["All"] + sorted(df["sex"].unique().tolist()) # These are here to create an option where
    age_options = ["All"] + sorted(df["age"].unique().tolist()) # you can sort by multiple aspects but can also
    colony_options = ["All"] + sorted(df["colony_type"].unique().tolist()) # filter only as necessary and leave
    condition_options = ["All"] + sorted(df["condition"].unique().tolist()) # other fields unfiltered
    treatment_options = ["All"] + sorted(df["treatment"].unique().tolist())

    st.header("Descriptive Statistics")
    selected_gender = st.selectbox("Gender:", gender_options, key="stats_gender")
    selected_age = st.selectbox("Age:", age_options, key="stats_age")
    selected_colony = st.selectbox("Colony type:", colony_options, key="stats_colony")
    selected_condition = st.selectbox("Condition:", condition_options, key="stats_condition")
    selected_treatment = st.selectbox("Treatment:", treatment_options, key="stats_treatment")

    filtered = df.copy()
    if selected_gender != "All": # We start from a full copy and narrow down one filter at a time; this only applies a
        filtered = filtered[filtered["sex"] == selected_gender] # filter when the user picked something other than "All."
    if selected_age != "All":
        filtered = filtered[filtered["age"] == selected_age]
    if selected_colony != "All":
        filtered = filtered[filtered["colony_type"] == selected_colony]
    if selected_condition != "All":
        filtered = filtered[filtered["condition"] == selected_condition]
    if selected_treatment != "All":
        filtered = filtered[filtered["treatment"] == selected_treatment]

    if filtered.empty:
        st.warning("No data matches this combination.")
        return

    stats = filtered.groupby("colony_type")["sample_count"].agg(
        mean="mean",
        std_dev="std",
        minimum="min",
        maximum="max",
        median="median",
        n_samples="count"
    ).reset_index()

    st.dataframe(stats, use_container_width=True, hide_index=True)


def main():
    connection = sqlite3.connect("cell-database.db")
    connCur = connection.cursor()
    MakeInitAnalysis(connCur) # Part 1's table construction
    MakeStatAnalysis(connCur) # Part 2's table construction
    MakeDashboard() # Construction of the streamlit dashboard
    renderComparisonSection() # Part 3's graph and table construction
    renderBaselineSummary() # Part 4's graph and table construction
    renderDescriptiveStats() # Measures metrics including those used in the bonus question.
    connection.commit()
    connection.close()

if __name__ == "__main__":
    main()