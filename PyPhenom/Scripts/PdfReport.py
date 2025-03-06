import PyPhenom as ppi
import subprocess
import random

pdf = ppi.Pdf.Document()
pdf.SetPageMode(ppi.Pdf.PageMode.UseOutline)

page = ppi.Pdf.Document.AddPage(pdf)
page.SetSize(ppi.Pdf.PageSize.A4)
height, width = page.GetHeight(),page.GetWidth()

page.BeginText()
page.SetFontAndSize(pdf.GetFont('Times-Bold'), 14)

page.MoveTextPos(50, height - 58)
page.ShowText('1. Example of an PDF-report generated with PPI')


page.MoveTextPos(0,-18)
page.SetFontAndSize(pdf.GetFont('Times-BoldItalic'), 12)
page.ShowText('1.1 Example of a long text')

longText = 'This report shows the powers of PPI and creating reports in Python. In this first section we show a long text that automatically is shown over multiple lines. In the second section we show a table filled with random data. The report is concluded by an image of a simulated image.'

page.SetFontAndSize(pdf.GetFont('Times-Roman'), 12)
page.TextRect(ppi.RectangleD(50,height-84,width-50,50),longText,ppi.Pdf.TextAlignment.Justify)


page.MoveTextPos(0,-32)
page.SetFontAndSize(pdf.GetFont('Times-BoldItalic'), 12)
page.ShowText('1.2 Example of a table')

page.MoveTextPos(0, -16)
page.SetFontAndSize(pdf.GetFont('Times-Roman'), 12)
page.ShowText('Row #')
page.MoveTextPos(64, 0)
page.ShowText('Value 1')
page.MoveTextPos(64, 0)
page.ShowText('Value 2')
page.MoveTextPos(64, 0)
page.ShowText('Value 3')
page.MoveTextPos(64, 0)
page.ShowText('Value 4')

xTableStart = page.GetCurrentTextPos().x
yTableStart = page.GetCurrentTextPos().y

page.EndText()

page.MoveTo(50,yTableStart-4)
page.LineTo(350,yTableStart-4)
page.Stroke()

page.BeginText()
page.MoveTextPos(xTableStart-32,yTableStart)
for row in range(5):
    page.MoveTextPos(-256, -16)
    page.ShowText(str(row+1))
    page.MoveTextPos(64, 0)
    page.ShowText(str('{:1.3f}'.format(random.random()*1)))
    page.MoveTextPos(64, 0)
    page.ShowText(str('{:1.1f}'.format(random.random()*2)))
    page.MoveTextPos(64, 0)
    page.ShowText(str('{:1.1f}'.format(random.random()*4)))
    page.MoveTextPos(64, 0)
    page.ShowText(str('{:1.0f}'.format(random.random()*8)))

yTableStop = page.GetCurrentTextPos().y

page.EndText()
page.MoveTo(50,yTableStop-4)
page.LineTo(350,yTableStop-4)
page.Stroke()
page.MoveTo(50,yTableStop-6)
page.LineTo(350,yTableStop-6)
page.Stroke()

page.BeginText()
page.MoveTextPos(50,yTableStop-32)
page.SetFontAndSize(pdf.GetFont('Times-BoldItalic'), 12)
page.ShowText('1.3 Example of a figure')

yPosFigure = page.GetCurrentTextPos().y

page.MoveTextPos(0,-(width-100)/2-16)
page.SetFontAndSize(pdf.GetFont('Times-Italic'), 12)
page.ShowText('Figure 1. PPI simulator image')

page.EndText()

phenom = ppi.Phenom('')
acq = phenom.SemAcquireImage(1024, 1024, 16)
page.DrawImage(acq.image, 50, yPosFigure-(width-100)/2-4, (width-100)/2, (width-100)/2)

pdf.SaveToFile('Example report manual.pdf')
subprocess.Popen('Example report manual.pdf', shell=True)
