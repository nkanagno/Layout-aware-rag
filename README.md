# Layout-aware-rag


## How to run and set up
To run the application, you need to set up your Python environment, configure your OpenAI API key, and then execute it via the command line.
### Set up python
First set up your python environment with the following command
```
python -m venv myenv
```
and activate it with
```
source myenv/bin/activate
```
on Linux/Mac users or 
```
myenv\Scripts\activate
```
for window users.

After activation, you can install the applications requirements (python 3.10.0 recommended) with:
```
pip install -r requirements.txt
```

### Configure your OpenAi api key

To configure your OpenAI API key, navigate to the main [OpenAI platform website](https://platform.openai.com/).

After obtaining your API key, add it to a `.env` file in your project root with the following format:
```
OPENAI_API_KEY=your_api_key_here
```

### Run webapp.py
To run the application you should enter the following command to your terminal:
```
streamlit run webapp.py
```
