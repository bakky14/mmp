import mysql.connector
import pandas as pd
from sklearn.model_selection import GridSearchCV
import json
from notebook import notebookapp
import urllib
import os
import ipykernel
import nbformat
from nbconvert import PythonExporter

INSERT_SQL = "INSERT INTO train_logs " + \
             "(train_name, params, train_models, score, features, train_sample, source) " + \
             "VALUES (%s, %s, %s, %s, %s, %s, %s) "

SELECT_SQL = "SELECT train_name, train_models, params, score, features, train_sample, insert_datetime source " + \
             "FROM train_logs " + \
             "ORDER BY insert_datetime DESC LIMIT %s, %s "
        
def notebook_path():
    """Returns the absolute path of the Notebook or None if it cannot be determined
    NOTE: works only when the security is token-based or there is also no password
    """
    connection_file = os.path.basename(ipykernel.get_connection_file())
    kernel_id = connection_file.split('-', 1)[1].split('.')[0]

    for srv in notebookapp.list_running_servers():
        try:
            if srv['token']=='' and not srv['password']:  # No token and no password, ahem...
                req = urllib.request.urlopen(srv['url']+'api/sessions')
            else:
                req = urllib.request.urlopen(srv['url']+'api/sessions?token='+srv['token'])
            sessions = json.load(req)
            for sess in sessions:
                if sess['kernel']['id'] == kernel_id:
                    return os.path.join(srv['notebook_dir'],sess['notebook']['path'])
        except:
            pass  # There may be stale entries in the runtime directory 
    return None        

def convertNotebook(notebookPath):

  with open(notebookPath, encoding='UTF-8') as fh:
    nb = nbformat.reads(fh.read(), nbformat.NO_CONVERT)

  exporter = PythonExporter()
  source, meta = exporter.from_notebook_node(nb)

  return source


def get_connection():
    return mysql.connector.connect(
      host="101.101.165.147",
      user="south4",
      passwd="southpaw",
      database="south4"
    )

def get_cursor(conn):
    return conn.cursor()

def insert(train_name:str, params:str, train_models:str, score:float, features:str, train_sample:str, source:str=''):
    """로그 입력"""
    try:
        conn = get_connection()
        cursor = get_cursor(conn)
        score = float(score)
        val = (train_name, params, train_models, score,features,train_sample, source)
        cursor.execute(INSERT_SQL, val)
        conn.commit()
    
    except mysql.connector.Error as error :
        conn.rollback() #rollback if any exception occured
        print("Failed inserting record into python_users table {}".format(error))  
    
    finally:
        if(conn.is_connected()):
            cursor.close()
            conn.close()

def save(train_name:str, X_train:pd.DataFrame, clfs:list, clf_cv:GridSearchCV):
    params = json.dumps(clf_cv.best_params_)
    score = clf_cv.best_score_
    clfs_models = [i[0] for i in clfs]
    train_models = json.dumps(clfs_models)
    features = json.dumps(list(X_train.columns.values))
    train_sample = X_train.sample(n=3).to_json(orient='table')
    notebookPath = notebook_path()  
    source = convertNotebook(notebookPath)
    insert(train_name, params, train_models, score, features, train_sample, source)

def get(limit:int = 10)->pd.DataFrame:
    conn = get_connection()
    cursor = get_cursor(conn)
    cursor.execute(SELECT_SQL, (0, limit))
    sql_data = pd.DataFrame(cursor.fetchall())
    sql_data.columns = cursor.column_names
    return sql_data

    #insert("train_test3", "params", "train_models", "source")
#print(cursor_south4.rowcount, "record inserted.")

