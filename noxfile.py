import nox

python_versions = ["3.11", "3.10"]

@nox.session(python=python_versions)
def test(session):
    session.install(".")
    session.install("pytest")
    session.run("pytest")

@nox.session(python=python_versions)
def lint(session):
    session.install("flake8")
    session.run("flake8", "src", "tests", "noxfile.py")

@nox.session(python=python_versions[0])
def format(session):
    session.install("black", "isort")
    session.run("black", "src", "tests")
    session.run("isort", "src", "tests")

@nox.session(python=python_versions[0])
def types(session):
    session.install(".")
    session.install("mypy")
    session.run("mypy", "src", "tests")
