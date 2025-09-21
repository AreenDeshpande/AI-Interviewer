try:
    # When run from project root: `python -m backend.app` or `python backend/app.py`
    from backend import create_app
except ImportError:
    # When run from inside backend folder: `python app.py`
    import os
    import sys
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from backend import create_app


app = create_app()


if __name__ == '__main__':
    app.run(debug=True)


