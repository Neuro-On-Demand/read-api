from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import (
    LambdaFunctionUrlResolver,
    Response,
    content_types,
)
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext
from http import HTTPStatus
from boto3 import client
import os

tracer = Tracer()
logger = Logger()
app = LambdaFunctionUrlResolver()


@app.route("/preupload", method=["GET"])
@tracer.capture_method
def upload():
    bucket: str = os.environ.get("BUCKET", "")
    body: dict = app.current_event.json_body
    key_prefix: str = body.get("name")

    if key_prefix:
        key = f"{key_prefix}-{app.current_event.request_context.request_id}"
    else:
        resp_body = "Name key is not part of the request."
        return Response(
            status_code=HTTPStatus.BAD_REQUEST,
            content_type=content_types.APPLICATION_JSON,
            body=resp_body,
        )

    s3_client = client(service_name="s3")
    presigned_body: dict = s3_client.generate_presigned_post(Bucket=bucket, Key=key)

    url: str = presigned_body.get("url")
    fields: dict = presigned_body.get("fields")

    if url and fields:
        body = {"url": url, "key": key, "fields": fields}

        logger.info(msg="", **body)

        url = url.replace("\\/", "/")
        return Response(
            status_code=HTTPStatus.ACCEPTED,
            content_type=content_types.APPLICATION_JSON,
            body=body,
        )
    else:
        return Response(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            content_type=content_types.APPLICATION_JSON,
            body="URL could not be generated.",
        )


# You can continue to use other utilities just as before
@logger.inject_lambda_context(correlation_id_path=correlation_paths.LAMBDA_FUNCTION_URL)
@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    return app.resolve(event, context)
