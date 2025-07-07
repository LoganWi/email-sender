from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import smtplib
from email.message import EmailMessage
import os

app = FastAPI()

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://americaro.imweb.me", "http://localhost:3000", "http://localhost:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MailRequest(BaseModel):
    file_url: str
    biz_name: str
    sender_email: str

class MailRequestBase64(BaseModel):
    pdf_base64: str
    biz_name: str
    sender_email: str

@app.post("/send-email")
def send_email(data: MailRequest):
    try:
        # PDF 다운로드
        response = requests.get(data.file_url)
        if response.status_code != 200:
            return {"success": False, "message": "파일 다운로드 실패"}

        # 이메일 구성
        msg = EmailMessage()
        msg["Subject"] = f"견적서 발송 - {data.biz_name} | {data.sender_email}"
        msg["From"] = os.environ.get("SMTP_USER")
        msg["To"] = "abc@americaro.co.kr"
        msg.set_content(f"""
        안녕하세요.
        {data.biz_name} 고객님이 견적서를 요청하셨습니다.

        이메일: {data.sender_email}
        """)

        # 첨부파일
        msg.add_attachment(
            response.content,
            maintype='application',
            subtype='pdf',
            filename=f"견적서_{data.biz_name}.pdf"
        )

        # 메일 전송
        smtp_host = "smtp.worksmobile.com"
        smtp_port = 465
        smtp_user = os.environ.get("SMTP_USER")
        smtp_pass = os.environ.get("SMTP_PASS")

        with smtplib.SMTP_SSL(smtp_host, smtp_port) as smtp:
            smtp.login(smtp_user, smtp_pass)
            smtp.send_message(msg)

        return {"success": True, "message": "메일 발송 성공"}

    except Exception as e:
        return {"success": False, "message": f"에러 발생: {str(e)}"}

@app.post("/send-email-base64")
def send_email_base64(data: MailRequestBase64):
    try:
        import base64
        
        # base64 디코딩
        pdf_content = base64.b64decode(data.pdf_base64)
        
        # 이메일 구성
        msg = EmailMessage()
        msg["Subject"] = f"견적서 발송 - {data.biz_name} | {data.sender_email}"
        msg["From"] = os.environ.get("SMTP_USER")
        msg["To"] = "placeja@gmail.com"
        msg.set_content(f"""
        안녕하세요.
        {data.biz_name} 고객님이 견적서를 요청하셨습니다.

        이메일: {data.sender_email}
        """)

        # 첨부파일
        msg.add_attachment(
            pdf_content,
            maintype='application',
            subtype='pdf',
            filename=f"견적서_{data.biz_name}.pdf"
        )

        # 메일 전송
        smtp_host = "smtp.worksmobile.com"
        smtp_port = 465
        smtp_user = os.environ.get("SMTP_USER")
        smtp_pass = os.environ.get("SMTP_PASS")

        with smtplib.SMTP_SSL(smtp_host, smtp_port) as smtp:
            smtp.login(smtp_user, smtp_pass)
            smtp.send_message(msg)

        return {"success": True, "message": "메일 발송 성공"}

    except Exception as e:
        return {"success": False, "message": f"에러 발생: {str(e)}"}
