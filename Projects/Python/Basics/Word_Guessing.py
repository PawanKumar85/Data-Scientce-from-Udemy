# Objective : Practice string manipulation and loops.
# Concepts: Lists, user input validation, ASCII art.

import random

class WordGuessGame:
    def __init__(self):
        self.words = ["python", "developer", "computer", "science", "keyboard", "internet", "Word", "program","Guess","Game"]
        self.max_attempts = 10
        self.word_to_guess = random.choice(self.words)
        self.guess_letters = []
        self.remaining_attempts = self.max_attempts
        
    
    def display_word(self):
        display = ""   
        for i in self.word_to_guess:
            if i in self.guess_letters:
                display += i + " "
            else:
                display += "_"
            
        return display.strip()
    
    def get_user_input(self):
        try:
            guess = input("Enter : ").lower()
            
            if len(guess) != 1 or not guess.isalpha():
                raise ValueError("Please enter a single alphabetical character.")
            return guess
        
        except ValueError as ve:
            print("Error :",ve)
            return self.get_user_input()
        except Exception as e:
            print("Error :",e)
            return self.get_user_input()
        
    def play(self):
        print("🎮 === Welcome to the Word Guessing Game! === 🎮")
        print(f"The word has {len(self.word_to_guess)} letters.")
        
        try:
            while self.max_attempts > 0:
                print("\nWord:", self.display_word())
                print(f"Remaining Attempts : {self.max_attempts}")
                print("Guess Letter :",", ".join(self.guess_letters))
                
                guess = self.get_user_input()
                
                if guess in self.guess_letters:
                    print("You've already guessed that letter.")
                    continue
                self.guess_letters.append(guess)
                
                if guess in self.word_to_guess:
                    print("Correct Guess")
                else:
                    self.remaining_attempts -= 1
                    print("Incorrect Guess")
                
                if all(letter in self.guess_letters for letter in self.word_to_guess):
                     print("\nCongratulations! You've guessed the word:", self.word_to_guess)
                     break
            else:
                print("\nOut of attempts! The word was:", self.word_to_guess)

        except KeyboardInterrupt :
            print("\nGame interrupted by user.")
        except Exception as e:
            print("Error : ",e)
        finally:
            print("Thanks for Playing...!!")
        
    
try:
    game = WordGuessGame()
    game.play()
except Exception as e:
    print("Critical Error : ",e)                