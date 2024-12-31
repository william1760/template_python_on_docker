import os

class ConsoleTitle:
    @staticmethod
    def show_title(subject: str, clear_screen: bool = False, dash_count: int = 50):
        """
        Generate the title with dashes surrounding the message.

        Parameters:
            subject (str): The title name.
            dash_count (int): The number of dashes on each side of the subject.
            clear_screen (bool): A flag to clear the screen before printing the title.
        """
        if clear_screen:
            ConsoleTitle.clear_screen()

        dashes = '/' * dash_count
        title = f'{dashes}  {subject}  {dashes}'
        print(f'\n{title}\n')

    @staticmethod
    def clear_screen():
        """
        Clear the console screen.

        Note: This implementation may not work on all platforms.
        """
        if os.name == 'posix':
            # For Unix-based systems (macOS, Linux)
            print('\033[H\033[J')
        elif os.name == 'nt':
            # For Windows
            os.system('cls')
        else:
            # Fallback for other systems (may not work on all platforms)
            print('\n' * 100)  # Print newlines to clear the screen


if __name__ == "__main__":
    ConsoleTitle.show_title("This is title1", True, 30)
    ConsoleTitle.show_title("This is title2", False, 50)
    ConsoleTitle.show_title("This is title3", False, 80)