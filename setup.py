from setuptools import setup, find_packages
from version import get_git_version


setup(
    name="stoxy.server",
    version=get_git_version(),
    description="""CDMI Storage Proxy (Stoxy)""",
    author="Ilja Livenson and Co",
    author_email="ilja.livenson@gmail.com",
    packages=find_packages(),
    namespace_packages=['stoxy'],
    zip_safe=False,  # martian grok scan is incompatible with zipped eggs
    entry_points={'oms.plugins': ['stoxy = stoxy.server:StoxyPlugin']},
    install_requires=[
        "setuptools",  # Redundant but removes a warning
        "opennode.oms.core"
        ],

)
