# Objective: Master syntax, variables, and user input.
# Concepts: print(), arithmetic operations, conditional statements.

class Math:
    def __init__(self, x, y):
        try:
            self.x = float(x)
            self.y = float(y)
        except ValueError:
            raise ValueError("Invalid Input...! Please Enter Numeric Values Only.")
    
    def add(self):
        return self.x + self.y

    def sub(self):
        return self.x - self.y

    def div(self):
        if self.y == 0:
            raise ZeroDivisionError("Cannot divide by zero.")
        return self.x / self.y

    def multi(self):
        return self.x * self.y


while True:
    print("""
    === Simple Calculator ===
    1. Addition
    2. Subtraction
    3. Multiplication
    4. Division
    5. Exit
    """)
    
    choice = input("Enter your Choice (1 - 5): ")
    
    if choice == '5':
        print("Exiting the calculator. Goodbye!")
        break
    
    if choice in ['1', '2', '3', '4']:
        x = input("Enter First Number: ")
        y = input("Enter Second Number: ")
        
        try:
            calc = Math(x, y)
            
            if choice == '1':
                print("Result:", calc.add())
            elif choice == '2':
                print("Result:", calc.sub())
            elif choice == '3':
                print("Result:", calc.multi())
            elif choice == '4':
                print("Result:", calc.div())
                 
        except ValueError as ve:
            print("Input Error:", ve)
        except ZeroDivisionError as ze:
            print("Math Error:", ze)
        except Exception as e:
            print("Error:", e)
    else:
        print("Invalid choice! Please select from 1 to 5.")
    
    print("\n-------------------------\n")
