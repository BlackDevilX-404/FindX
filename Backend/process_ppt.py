from pathlib import Path
import aspose.slides as slides


class Ppt2Pdf:
    def __init__(self, name, ext):
        self.name = name
        self.ext = ext

    def convert_ppt_to_pdf(self):
        BASE_DIR = Path(__file__).resolve().parent

        input_path = BASE_DIR /  f"{self.name}.{self.ext}"
        output_path = BASE_DIR /  f"{self.name}.pdf"

        print("Input:", input_path)
        print("Output:", output_path)

        try:
            presentation = slides.Presentation(str(input_path))
            presentation.save(str(output_path), slides.export.SaveFormat.PDF)
            print("✅ Successfully converted to PDF")
        except Exception as e:
            print("❌ Error:", e)


if __name__ == "__main__":
    obj = Ppt2Pdf("ExplainX-Universal-Multimodal-Content-Explainer (1)", "pptx")
    obj.convert_ppt_to_pdf()
