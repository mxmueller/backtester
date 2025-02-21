from fastapi import FastAPI, HTTPException
import papermill as pm
import scrapbook as sb

app = FastAPI()

@app.post("/execute")
async def execute_notebook():
    try:
        pm.execute_notebook(
            'demo.ipynb',
            'output.ipynb',
            parameters={
                'base_number': 50,
                'multiplier': 5
            }
        )
        nb = sb.read_notebook('../output.ipynb')
        result = nb.scraps.data_dict['result']
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))