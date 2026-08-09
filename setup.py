from setuptools import setup, find_packages

setup(
    name='google-tasks-widget',
    version='1.0.0',
    description='A transparent desktop widget for Google Tasks (Unofficial Client)',
    author='Antigravity',
    py_modules=['main', 'auth', 'cli', 'mcp_server'],
    package_data={
        '': ['resources/*'],
    },
    include_package_data=True,
    install_requires=[
        'google-api-python-client>=2.100.0',
        'google-auth-httplib2>=0.1.0',
        'google-auth-oauthlib>=1.1.0',
        'PyQt5>=5.15.0',
        'mcp>=1.0.0'
    ],
    entry_points={
        'console_scripts': [
            'google-tasks-widget=main:main',
            'google-tasks-cli=cli:main',
            'google-tasks-mcp=mcp_server:main',
        ],
    },
)
