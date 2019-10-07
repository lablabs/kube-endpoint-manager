import os
import setuptools


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

REQUIRES = []
with open('requirements.txt') as f:
    for line in f:
        line, _, _ = line.partition('#')
        line = line.strip()
        if ';' in line:
            requirement, _, specifier = line.partition(';')
            for_specifier = EXTRAS.setdefault(':{}'.format(specifier), [])
            for_specifier.append(requirement)
        else:
            REQUIRES.append(line)

setuptools.setup(
    name="kube_endpoint_manager",
    version="0.0.1",
    author="Martin Dojcak",
    author_email="martin.dojcak@lablabs.io",
    description="Kubernetes external endpoint manager",
    long_description=read('README.md'),
    long_description_content_type="text/markdown",
    url="https://github.com/lablabs/kube-endpoint-manager",
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': [
            'kube-endpoint-manager = kube_endpoint_manager.__main__:main',
        ],
    },
    install_requires=REQUIRES,
    classifiers=[
        "Programming Language :: Python :: 3",
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Topic :: System :: Networking',
        'Topic :: System :: Installation/Setup',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python',
    ],
)