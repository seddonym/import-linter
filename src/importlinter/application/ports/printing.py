import abc


class Printer(abc.ABC):
    ERROR = 'error'
    SUCCESS = 'success'

    HEADING_LEVEL_ONE = 1
    HEADING_LEVEL_TWO = 2
    HEADING_LEVEL_THREE = 3
    HEADING_LEVELS = (HEADING_LEVEL_ONE, HEADING_LEVEL_TWO, HEADING_LEVEL_THREE)

    @abc.abstractmethod
    def print(self, text, bold=False):
        """
        Prints a line.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def print_heading(self, text, level, style=None):
        """
        Prints the supplied text formatted as a heading.

        Args:
            text (str): the text to format as a heading.
            level (int): the level of heading to display (one of HEADING_LEVELS).
            style (str, optional): ERROR or SUCCESS style to apply (default None).
        """
        raise NotImplementedError
    
    @abc.abstractmethod
    def print_success(self, text, bold=True):
        """
        Prints the text formatted as a success.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def print_error(self, text, bold=True):
        """
        Prints the text formatted as an error.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def indent_cursor(self):
        """
        Indents the cursor ready to print some text.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def new_line(self):
        raise NotImplementedError
