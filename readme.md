pip freeze > deletedRequirements.txt
pip uninstall -y -r deletedRequirements.txt
python -m src.core.client