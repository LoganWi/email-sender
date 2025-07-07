from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import smtplib
from email.message import EmailMessage
import os
import threading
from contextlib import contextmanager

app = FastAPI()

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://americaro.imweb.me", "http://localhost:3000", "http://localhost:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SMTP 연결 풀 관리
class SMTPPool:
    def __init__(self):
        self.connections = {}
        self.lock = threading.Lock()
    
    @contextmanager
    def get_connection(self):
        thread_id = threading.get_ident()
        
        with self.lock:
            if thread_id not in self.connections:
                # 새 연결 생성
                smtp_host = "smtp.worksmobile.com"
                smtp_port = 465
                smtp_user = os.environ.get("SMTP_USER")
                smtp_pass = os.environ.get("SMTP_PASS")
                
                smtp = smtplib.SMTP_SSL(smtp_host, smtp_port)
                smtp.login(smtp_user, smtp_pass)
                self.connections[thread_id] = smtp
            
            connection = self.connections[thread_id]
        
        try:
            yield connection
        except Exception as e:
            # 연결 오류 시 재생성
            with self.lock:
                if thread_id in self.connections:
                    try:
                        self.connections[thread_id].quit()
                    except:
                        pass
                    del self.connections[thread_id]
            raise e

# 전역 SMTP 풀 인스턴스
smtp_pool = SMTPPool()

class MailRequestBase64(BaseModel):
    pdf_base64: str
    biz_name: str
    sender_email: str

def send_email_background(msg):
    with smtp_pool.get_connection() as smtp:
        smtp.send_message(msg)

@app.post("/send-email-base64")
def send_email_base64(data: MailRequestBase64, background_tasks: BackgroundTasks):
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

        # 비동기로 전송
        background_tasks.add_task(send_email_background, msg)

        return {"success": True, "message": "메일 발송 요청이 접수되었습니다."}

    except Exception as e:
        return {"success": False, "message": f"에러 발생: {str(e)}"}
