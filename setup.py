from pathlib import Path

from setuptools import setup


README = Path(__file__).with_name("readme.md")

setup(
    name="fluid-agent-pro",
    version="0.1.0",
    description="Research workflow controller for industrial defect detection projects",
    long_description=README.read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    py_modules=["fluid_agent_pro", "fluid_agent_pro_gui"],
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "fluid-agent-pro=fluid_agent_pro:main",
            "fluid-agent-pro-gui=fluid_agent_pro_gui:main",
        ]
    },
    extras_require={
        "gui": ["PySide6>=6.7"],
        "packager": ["PyInstaller>=6.0"],
    },
)
