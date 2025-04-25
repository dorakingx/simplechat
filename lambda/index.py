# lambda/index.py
import json
import os
import re                       # --- そのまま残す
import urllib.request           # ★ 追加：FastAPI を呼び出すため
import urllib.error             # ★ 追加：エラーハンドリング用
# boto3 や Bedrock 関連の import は不要になったので削除
# import boto3
# from botocore.exceptions import ClientError


# Lambda コンテキストからリージョンを抽出する関数（残しても支障なし）
def extract_region_from_arn(arn):
    # ARN 形式: arn:aws:lambda:region:account-id:function:function-name
    match = re.search(r'arn:aws:lambda:([^:]+):', arn)
    if match:
        return match.group(1)
    return "us-east-1"  # デフォルト値


# --- Bedrock 関連のグローバル変数を削除 -----------------------------
# bedrock_client = None
# MODEL_ID       = os.environ.get("MODEL_ID", "us.amazon.nova-lite-v1:0")

# ★ 追加：FastAPI のエンドポイントを環境変数から取得

FASTAPI_URL = "https://410d-2400-2411-9961-7200-899d-3479-5de9-608d.ngrok-free.app/startup"


def lambda_handler(event, context):
    try:
        # ------------------------------------------------------------
        # 受信イベントの確認
        # ------------------------------------------------------------
        print("Received event:", json.dumps(event))

        # Cognitoで認証されたユーザー情報を取得（元コードを維持）
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")

        # ------------------------------------------------------------
        # リクエストボディの解析
        # ------------------------------------------------------------
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])

        print("Processing message:", message)

        # ------------------------------------------------------------
        # FastAPI へ送信するペイロードを準備
        # ------------------------------------------------------------
        fastapi_payload = {
            "message": message,
            "conversationHistory": conversation_history
        }
        json_payload = json.dumps(fastapi_payload).encode("utf-8")

        # ------------------------------------------------------------
        # FastAPI エンドポイント呼び出し
        # ------------------------------------------------------------
        print(f"Calling FastAPI at {FASTAPI_URL} with payload:", json_payload.decode())
        req = urllib.request.Request(
            url=FASTAPI_URL,
            data=json_payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=30) as res:
            response_body = json.loads(res.read().decode("utf-8"))

        print("FastAPI response:", json.dumps(response_body, default=str))

        # ------------------------------------------------------------
        # FastAPI 応答の検証
        # ------------------------------------------------------------
        if not response_body.get("success"):
            raise Exception(f"FastAPI error: {response_body.get('error', 'Unknown error')}")

        assistant_response   = response_body.get("response", "")
        updated_conversation = response_body.get("conversationHistory", [])

        # ------------------------------------------------------------
        # 成功レスポンスの返却
        # ------------------------------------------------------------
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": updated_conversation
            })
        }

    # ------------------------------------------------------------
    # エラーハンドリング
    # ------------------------------------------------------------
    except urllib.error.HTTPError as e:
        error_msg = f"HTTPError {e.code}: {e.reason}"
        print("Error:", error_msg)
        return {
            "statusCode": 502,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": error_msg
            })
        }

    except urllib.error.URLError as e:
        error_msg = f"URLError: {e.reason}"
        print("Error:", error_msg)
        return {
            "statusCode": 504,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": error_msg
            })
        }

    except Exception as error:
        print("Error:", str(error))
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }
