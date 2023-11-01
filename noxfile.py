import nox

python_versions = ["3.11", "3.10"]

@nox.session(python=python_versions)
def tests(session):
    session.install(".")
    session.install("pytest")
    session.run("pytest")
