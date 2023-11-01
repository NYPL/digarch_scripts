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
