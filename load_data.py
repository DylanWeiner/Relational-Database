#!.venv/bin python3
import csv
import sqlite3

#Schema:
#sampleMetadata['sample', 'project', 'subject', 'condition', 'age', 'sex']
#conditionDeets['sample', 'treatment', 'response', 'sample_type', 'time_from_treatment_start']
#immunePops['sample', 'b_cell', 'cd8_t_cell', 'cd4_t_cell', 'nk_cell', 'monocyte']

def create_database(db_name): # Helper function to create database.
    with sqlite3.connect(db_name) as connection: # Creates pipeline to the file
        connCur = connection.cursor() # Cursor will step through our rows in our SQL database
        connCur.execute("PRAGMA foreign_keys = ON;") # Allows the use of foreign keys for inter-table communication
        connCur.execute("""
                        CREATE TABLE IF NOT EXISTS sampleMetadata (
                        sample VARCHAR(11) PRIMARY KEY,
                        project VARCHAR NOT NULL,
                        subject VARCHAR NOT NULL,
                        condition VARCHAR NOT NULL,
                        age INTEGER(3) NOT NULL,
                        sex VARCHAR(1) NOT NULL
                        );
        """) # Creates table for sample metadata regarding the patient.
        connCur.execute("""
                        CREATE TABLE IF NOT EXISTS conditionDeets (
                        sample VARCHAR(11) PRIMARY KEY,
                        treatment VARCHAR NOT NULL,
                        response VARCHAR,
                        sample_type VARCHAR NOT NULL,
                        time_from_treatment_start INTEGER NOT NULL,
                        FOREIGN KEY (sample) REFERENCES sampleMetadata(sample)
                        );
        """) # Creates a table for condition details regarding treatement.
        connCur.execute("""
                        CREATE TABLE IF NOT EXISTS immunePops (
                        sample VARCHAR PRIMARY KEY,
                        b_cell VARCHAR NOT NULL,
                        cd8_t_cell VARCHAR NOT NULL,
                        cd4_t_cell VARCHAR NOT NULL,
                        nk_cell VARCHAR NOT NULL,
                        monocyte VARCHAR NOT NULL,
                        FOREIGN KEY (sample) REFERENCES sampleMetadata(sample)
                        );
        """) # Creates a table for condition immune cell populations.
        with open("cell-count.csv", mode="r", encoding="utf-8") as csvFile:
            csv_reader = csv.DictReader(csvFile)
            for row in csv_reader: # Runs through each row and inserts values to the relevant cell.
                connCur.execute("INSERT INTO sampleMetadata (sample, project, subject, condition, age, sex) VALUES (:sample, :project, :subject, :condition, :age, :sex) ON CONFLICT(sample) DO NOTHING;", row,)
                connCur.execute("INSERT INTO conditionDeets (sample, treatment, response, sample_type, time_from_treatment_start) VALUES (:sample, :treatment, :response, :sample_type, :time_from_treatment_start) ON CONFLICT(sample) DO NOTHING;", row,)
                connCur.execute("INSERT INTO immunePops (sample, b_cell, cd8_t_cell, cd4_t_cell, nk_cell, monocyte) VALUES (:sample, :b_cell, :cd8_t_cell, :cd4_t_cell, :nk_cell, :monocyte) ON CONFLICT(sample) DO NOTHING;", row,)
    connection.commit() # Commits file
    connection.close() # Safely closes database



        

def main():
    create_database("cell-database.db")


if __name__ == "__main__":
    main() # Runs main function