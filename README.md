To open the dashboard, you need to type make all. This will parse the excel file into a relational database and then parse this relational database into the relevant tables and graphs with the ability to change to relevant ones to use the necessary filters. For instance, you can apply the filter to the box plot to search for all the rows with melanoma receiving miraclib treatment derived from PBMC samples.

The schema for my relational database was as follows:
sampleMetadata['sample', 'project', 'subject', 'condition', 'age', 'sex']
conditionDeets['sample', 'treatment', 'response', 'sample_type', 'time_from_treatment_start']
immunePops['sample', 'b_cell', 'cd8_t_cell', 'cd4_t_cell', 'nk_cell', 'monocyte']
I kept the patient information in one table so any personal identifying information would be centralized and otherwise out of the way. I kept details of patient treatment information in its own table to make it so monitoring outcomes of patient treatments centralized to the same table. The final table holds information on all of the cell colonies of each cell type. I kept the sample for all tables to simplify natural join functions and to use as a primary key for all of the tables. This should scale very well for larger projects as was mentioned since there is good and logical division amongst all of the tables to keep down runtime and any additional access will be under the scope of reading rather than writing which is far less demanding.



URL: http://localhost:8501

Any instructions needed to run your code and reproduce the outputs (We will run your code using GitHub Codespaces).

An explanation of the schema used for the relational database, with rationale for the design and how this would scale if there were hundreds of projects, thousands of samples and various types of analytics you’d want to perform.

A brief overview of your code structure and an explanation of why you designed it the way you did.

A link to the dashboard.