# Turtle Embroidery Playground

A minimal Flask web app that lets you prototype embroidery paths using a turtle-like API from `TurtleEmbroidery`.

## Features
- Write Python snippets with turtle commands (`forward`, `left`, `penup`, `goto`, loops, etc.).
- Tab support in the editor and auto-indentation after a colon.
- Live SVG preview rendered from the generated embroidery pattern.

## Getting started
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the server:
   ```bash
   python app.py
   ```
3. Open `http://localhost:5000` in your browser, edit the starter code, and click **Run pattern** to update the preview.

The app uses the `TurtleEmbroidery` class to build stitch points and renders them as SVG for quick iteration.
