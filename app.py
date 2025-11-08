#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ui.main_view import PDFToolboxApp
from controller.pdf_controller import PDFController

def main():
    controller = PDFController()
    app = PDFToolboxApp(controller)
    app.mainloop()

if __name__ == "__main__":
    main()
