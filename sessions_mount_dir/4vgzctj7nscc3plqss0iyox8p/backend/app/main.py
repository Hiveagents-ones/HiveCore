from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/api/product")
def get_product():
    return {
        "id": "R1",
        "title": "新品发布单页核心功能",
        "type": "功能",
        "details": "展示高清产品图片（至少1张）、产品详细描述（含功能、规格）、可点击的购买按钮（链接至支付页面）",
        "priority": "P1"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)