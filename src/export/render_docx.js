const fs = require("fs");
const path = require("path");
const {
  AlignmentType,
  Document,
  Footer,
  HeadingLevel,
  Packer,
  PageNumber,
  PageOrientation,
  Paragraph,
  TextRun,
} = require("docx");

function buildParagraphs(text) {
  return text
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map(
      (line) =>
        new Paragraph({
          spacing: { line: 420, after: 120 },
          indent: { firstLine: 420 },
          children: [
            new TextRun({
              text: line,
              font: "宋体",
              size: 24,
            }),
          ],
        })
    );
}

async function main() {
  const [, , payloadFile, outputFile, templateName] = process.argv;
  const payload = JSON.parse(fs.readFileSync(payloadFile, "utf8"));

  const children = [];
  children.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 240 },
      children: [
        new TextRun({ text: payload.title, bold: true, font: "黑体", size: 32 }),
      ],
    })
  );

  children.push(
    new Paragraph({
      alignment: AlignmentType.LEFT,
      spacing: { before: 120, after: 120 },
      children: [new TextRun({ text: "摘要", bold: true, font: "黑体", size: 28 })],
    })
  );
  children.push(...buildParagraphs(payload.abstract));

  children.push(
    new Paragraph({
      spacing: { after: 200 },
      children: [
        new TextRun({ text: "关键词：", bold: true, font: "黑体", size: 24 }),
        new TextRun({ text: payload.keywords.join("；"), font: "宋体", size: 24 }),
      ],
    })
  );

  for (const [title, body] of payload.sections) {
    children.push(
      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        spacing: { before: 240, after: 160 },
        children: [new TextRun({ text: title, font: "黑体", size: 28, bold: true })],
      })
    );
    children.push(...buildParagraphs(body));
  }

  children.push(
    new Paragraph({
      heading: HeadingLevel.HEADING_1,
      spacing: { before: 240, after: 160 },
      children: [new TextRun({ text: "参考文献", font: "黑体", size: 28, bold: true })],
    })
  );
  for (const ref of payload.references) {
    children.push(
      new Paragraph({
        spacing: { after: 100 },
        indent: { hanging: 420 },
        children: [new TextRun({ text: ref, font: "宋体", size: 24 })],
      })
    );
  }

  const doc = new Document({
    creator: "OpenCode",
    title: payload.title,
    description: `Generated with reference template: ${templateName}`,
    styles: {
      default: {
        document: {
          run: { font: "宋体", size: 24 },
          paragraph: { spacing: { line: 420 } },
        },
      },
      paragraphStyles: [
        {
          id: "Heading1",
          name: "Heading 1",
          basedOn: "Normal",
          next: "Normal",
          quickFormat: true,
          run: { font: "黑体", size: 28, bold: true },
          paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 0 },
        },
      ],
    },
    sections: [
      {
        properties: {
          page: {
            size: {
              width: 11906,
              height: 16838,
              orientation: PageOrientation.PORTRAIT,
            },
            margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
          },
        },
        footers: {
          default: new Footer({
            children: [
              new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [
                  new TextRun({ text: "第 ", font: "宋体", size: 20 }),
                  new TextRun({ children: [PageNumber.CURRENT], font: "宋体", size: 20 }),
                  new TextRun({ text: " 页", font: "宋体", size: 20 }),
                ],
              }),
            ],
          }),
        },
        children,
      },
    ],
  });

  const buffer = await Packer.toBuffer(doc);
  fs.writeFileSync(outputFile, buffer);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
