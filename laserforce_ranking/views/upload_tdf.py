from django.views import View
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest
from pathlib import Path

class UploadTDFView(View):
    def post(self, request):
        #logger.info("Uploading TDF")

        type = request.POST.get("type")
        file = request.FILES.get("upload_file")

        #logger.debug(f"Type: {type}")
        #logger.debug(f"File: {file}")

        if file is None:
            #logger.error("No file provided in the request.")
            return HttpResponseBadRequest("No file provided in the request.")

        if type == "sm5":
            target_path = "./tdfs/" + file.name
            self._create_file_from_request(file, target_path)
        elif type == "laserball":
            target_path = "./tdfs/" + file.name
            self._create_file_from_request(file, target_path)
        else:
            #logger.error(f"Unsupported type: {type}")
            return HttpResponseBadRequest(f"Unsupported type: {type}")

        #logger.info("Uploaded TDF successfully!")

        return HttpResponse("Uploaded!")

    def _create_file_from_request(self, request_file, target_path: str):
        """Reads the data from a request's file and stores it in a local file.

        Creates the path structure leading up to the target path if it doesn't
        exist already.

        Args:
            request_file: The file from the HTTP request.
            target_path: The path to store this file in. Can be relative.
        """
        filepath = Path(target_path)

        # Create the directory if it doesn't exist already.
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Write the file content to the target file.
        with filepath.open("wb") as f:
            for chunk in request_file.chunks():
                f.write(chunk)
