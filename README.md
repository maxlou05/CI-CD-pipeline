# NCYD Deployment Information Automation Tool

The CD pipeline uses the CLI provided by `table_api.py` to access the database.
The CD pipeline is configured in `.gitlab-ci.yml`, which tells GitLab what to do in the pipeline.
Anytime code is pushed, a pipeline is run (for CI), but it can also be manual (CD or clean-up actions).
