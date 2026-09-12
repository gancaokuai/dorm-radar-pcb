Option Explicit

Const PART_TEMPLATE = "C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2024\templates\gb_part.prtdot"
Const ASM_TEMPLATE = "C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2024\templates\gb_assembly.asmdot"
Const OUT_DIR = "F:\DormRadarCAD"

Dim swApp
Set swApp = CreateObject("SldWorks.Application")
swApp.Visible = False

Function mm(v)
    mm = v / 1000.0
End Function

Sub SelectFrontPlane(model)
    Dim feat, ok
    model.ClearSelection2 True
    Set feat = model.FirstFeature
    Do While Not feat Is Nothing
        If feat.GetTypeName2 = "RefPlane" Then
            ok = feat.Select2(False, 0)
            Exit Sub
        End If
        Set feat = feat.GetNextFeature
    Loop
End Sub

Sub NewSketch(model)
    SelectFrontPlane model
    model.SketchManager.InsertSketch True
End Sub

Sub ExtrudeBlind(model, depth)
    model.FeatureManager.FeatureExtrusion3 True, False, False, 0, 0, mm(depth), 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False
End Sub

Sub CutThroughAll(model)
    model.FeatureManager.FeatureCut4 True, False, True, 1, 0, 0.03, 0.03, False, False, False, False, 0, 0, False, False, False, False, False, False, True, False, False, False, 0, 0, False, False
End Sub

Sub SavePart(model, path)
    model.SaveAs3 path, 0, 0
    model.SaveAs3 Replace(path, ".SLDPRT", ".STL"), 0, 0
    model.SaveAs3 Replace(path, ".SLDPRT", ".STEP"), 0, 0
    WScript.Echo "Saved " & path
End Sub

Sub BuildBase(name, outerW, outerD, baseH, floorT, bossH, boardX, boardY, holeXs, holeYs)
    Dim model, x, y, i
    Set model = swApp.NewDocument(PART_TEMPLATE, 0, 0, 0)
    If model Is Nothing Then WScript.Echo "New base failed: " & name : WScript.Quit 1

    NewSketch model
    model.SketchManager.CreateCornerRectangle mm(0), mm(0), 0, mm(outerW), mm(outerD), 0
    ExtrudeBlind model, baseH

    NewSketch model
    model.SketchManager.CreateCornerRectangle mm(2), mm(2), 0, mm(outerW-2), mm(outerD-2), 0
    CutThroughAll model

    NewSketch model
    model.SketchManager.CreateCornerRectangle mm(0), mm(0), 0, mm(outerW), mm(outerD), 0
    ExtrudeBlind model, floorT

    NewSketch model
    For i = 0 To 3
        model.SketchManager.CreateCircleByRadius mm(holeXs(i)), mm(holeYs(i)), 0, mm(3.0)
    Next
    ExtrudeBlind model, floorT + bossH

    NewSketch model
    For i = 0 To 3
        model.SketchManager.CreateCircleByRadius mm(holeXs(i)), mm(holeYs(i)), 0, mm(1.1)
    Next
    CutThroughAll model

    SavePart model, OUT_DIR & "\" & name & "_Base.SLDPRT"
End Sub

Sub BuildCover(name, outerW, outerD, baseH, coverT, holeXs, holeYs, antX1, antY1, antX2, antY2, j1X1, j1Y1, j1X2, j1Y2, extraJson)
    Dim model, i
    Set model = swApp.NewDocument(PART_TEMPLATE, 0, 0, 0)
    If model Is Nothing Then WScript.Echo "New cover failed: " & name : WScript.Quit 1

    NewSketch model
    model.SketchManager.CreateCornerRectangle mm(0), mm(0), 0, mm(outerW), mm(outerD), 0
    ExtrudeBlind model, coverT

    NewSketch model
    model.SketchManager.CreateCornerRectangle mm(antX1), mm(antY1), 0, mm(antX2), mm(antY2), 0
    CutThroughAll model

    NewSketch model
    model.SketchManager.CreateCornerRectangle mm(j1X1), mm(j1Y1), 0, mm(j1X2), mm(j1Y2), 0
    If extraJson <> "" Then
        Dim parts, p
        parts = Split(extraJson, "|")
        For Each p In parts
            Dim vals
            vals = Split(p, ",")
            If vals(0) = "R" Then
                model.SketchManager.CreateCornerRectangle mm(CDbl(vals(1))), mm(CDbl(vals(2))), 0, mm(CDbl(vals(3))), mm(CDbl(vals(4))), 0
            End If
        Next
    End If
    CutThroughAll model

    NewSketch model
    For i = 0 To 3
        model.SketchManager.CreateCircleByRadius mm(holeXs(i)), mm(holeYs(i)), 0, mm(1.35)
    Next
    CutThroughAll model

    If extraJson <> "" Then
        parts = Split(extraJson, "|")
        For Each p In parts
            vals = Split(p, ",")
            If vals(0) = "C" Then
                NewSketch model
                model.SketchManager.CreateCircleByRadius mm(CDbl(vals(1))), mm(CDbl(vals(2))), 0, mm(CDbl(vals(3)))
                CutThroughAll model
            End If
        Next
    End If

    SavePart model, OUT_DIR & "\" & name & "_Cover.SLDPRT"
End Sub
Sub BuildAssembly(name, basePath, coverPath, baseH)
    Dim asm, c1, c2
    Set asm = swApp.NewDocument(ASM_TEMPLATE, 0, 0, 0)
    If asm Is Nothing Then WScript.Echo "New assembly failed: " & name : WScript.Quit 1
    Set c1 = asm.AddComponent5(basePath, 0, "", False, "", 0, 0, 0)
    Set c2 = asm.AddComponent5(coverPath, 0, "", False, "", 0, 0, mm(baseH))
    If c1 Is Nothing Or c2 Is Nothing Then WScript.Echo "Add component failed: " & name : WScript.Quit 1
    asm.SaveAs3 OUT_DIR & "\" & name & "_Enclosure.SLDASM", 0, 0
    asm.SaveAs3 OUT_DIR & "\" & name & "_Enclosure.STL", 0, 0
    asm.SaveAs3 OUT_DIR & "\" & name & "_Enclosure.STEP", 0, 0
    WScript.Echo "Saved " & OUT_DIR & "\" & name & "_Enclosure.SLDASM"
End Sub

' TX: board 70 x 42. Case origin adds 3.5 mm x and 15 mm y.
Dim txHoleX, txHoleY, rxHoleX, rxHoleY
txHoleX = Array(6.5, 70.5, 6.5, 70.5)
txHoleY = Array(18.0, 18.0, 54.0, 54.0)
rxHoleX = Array(6.5, 68.5, 6.5, 68.5)
rxHoleY = Array(18.0, 18.0, 54.0, 54.0)

BuildBase "TX", 77, 61, 22, 2, 3, 3.5, 15, txHoleX, txHoleY
BuildCover "TX", 77, 61, 22, 2, txHoleX, txHoleY, 39.5, 4.9, 67.5, 15.9, 14.5, 50.5, 24.5, 55.5, "R,50.5,51,58.5,57|R,62.5,35,70.5,43"
BuildAssembly "TX", OUT_DIR & "\TX_Base.SLDPRT", OUT_DIR & "\TX_Cover.SLDPRT", 22

BuildBase "RX", 75, 61, 22, 2, 3, 3.5, 15, rxHoleX, rxHoleY
BuildCover "RX", 75, 61, 22, 2, rxHoleX, rxHoleY, 39.5, 3.9, 67.5, 14.9, 32.5, 48.5, 42.5, 53.5, "R,56.5,38,64.5,46|C,17.5,50,2"
BuildAssembly "RX", OUT_DIR & "\RX_Base.SLDPRT", OUT_DIR & "\RX_Cover.SLDPRT", 22

WScript.Echo "All enclosures generated"
swApp.ExitApp







