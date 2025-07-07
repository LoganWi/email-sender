from fastapi import FastAPI, BackgroundTasks, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import smtplib
from email.message import EmailMessage
import os
import threading
from contextlib import contextmanager
import time

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
                
                smtp = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)
                smtp.login(smtp_user, smtp_pass)
                self.connections[thread_id] = smtp
            else:
                # 기존 연결 상태 확인
                try:
                    connection = self.connections[thread_id]
                    # 연결 상태 확인 (NOOP 명령어 사용)
                    connection.noop()
                except Exception:
                    # 연결이 끊어진 경우 재생성
                    try:
                        self.connections[thread_id].quit()
                    except:
                        pass
                    
                    smtp_host = "smtp.worksmobile.com"
                    smtp_port = 465
                    smtp_user = os.environ.get("SMTP_USER")
                    smtp_pass = os.environ.get("SMTP_PASS")
                    
                    smtp = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)
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
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            with smtp_pool.get_connection() as smtp:
                # 연결 상태 재확인
                try:
                    smtp.noop()
                except Exception:
                    # 연결이 끊어진 경우 예외 발생시켜 재연결 유도
                    raise Exception("SMTP 연결이 끊어졌습니다.")
                
                # 타임아웃 설정
                smtp.timeout = 30
                smtp.send_message(msg)
                print("이메일 전송 성공")
                return  # 성공하면 함수 종료
        except Exception as e:
            retry_count += 1
            print(f"이메일 전송 실패 (시도 {retry_count}/{max_retries}): {str(e)}")
            
            if retry_count >= max_retries:
                print(f"최대 재시도 횟수 초과. 이메일 전송 실패: {str(e)}")
                raise e
            
            # 재시도 전 잠시 대기 (점진적으로 증가)
            time.sleep(retry_count * 2)

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

@app.post("/send-email-file")
def send_email_file(
    pdf_file: UploadFile = File(...),
    biz_name: str = Form(...),
    sender_email: str = Form(...),
    background_tasks: BackgroundTasks = None
):
    try:
        # 파일 내용 읽기
        pdf_content = pdf_file.file.read()
        
        # 이메일 구성
        msg = EmailMessage()
        msg["Subject"] = f"견적서 발송 - {biz_name} | {sender_email}"
        msg["From"] = os.environ.get("SMTP_USER")
        msg["To"] = "placeja@gmail.com"
        msg.set_content(f"""
        안녕하세요.
        {biz_name} 고객님이 견적서를 요청하셨습니다.

        이메일: {sender_email}
        """)

        # 첨부파일
        msg.add_attachment(
            pdf_content,
            maintype='application',
            subtype='pdf',
            filename=f"견적서_{biz_name}.pdf"
        )

        # 비동기로 전송
        background_tasks.add_task(send_email_background, msg)

        return {"success": True, "message": "메일 발송 요청이 접수되었습니다."}

    except Exception as e:
        return {"success": False, "message": f"에러 발생: {str(e)}"}
