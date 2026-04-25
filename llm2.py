import boto3
import json

model_id = "anthropic.claude-3-haiku-20240307-v1:0"
prompt = "Describe the purpose of a 'hello world' program in one line."

client = boto3.client("bedrock-runtime", region_name="us-east-1")
native_request = {
    "anthropic_version": "bedrock-2023-05-31",
    "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
    "max_tokens": 4096,
    "temperature": 0
}
response = client.invoke_model(modelId=model_id, body=json.dumps(native_request))
model_response = json.loads(response["body"].read())
response_text = model_response["content"][0]["text"]
print(response_text)
