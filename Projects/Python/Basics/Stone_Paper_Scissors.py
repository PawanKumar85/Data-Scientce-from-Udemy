# Objective: Implement game logic with randomness.
# Concepts: random module, loops, conditionals.

import random

class StonePaperScissors:
    def __init__(self):
        self.choices = ["stone", "paper", "scissors"]
        self.user = 0
        self.pc = 0
        
    def get_user_input(self):
        try:
            choice = input("Enter your choice (stone/paper/scissors): ").lower()
            
            if choice in self.choices:
                print("\nEnter\n")
                return choice
            else:
                print("❌ Invalid choice! Please type: stone, paper, or scissors.")
                return self.get_user_input()
        except Exception as e:
            print("Error : ",str(e))
            return self.get_user_input()
        
    def get_pc(self):
        return random.choice(self.choices)
    
    def decide_winner(self, user, pc):
        if user == pc:
            return "draw"
        elif (user == "stone" and pc == "scissors") or (user == "scissors" and pc == "paper") or (user == "paper" and pc == "store") : 
            self.user += 1
            return "user"
        else:
            self.pc += 1
            return "pc"
    
    def play(self,round=5):
        print("🎮 === Stone Paper Scissors Game === 🎮")
        try:
            for i in range(1,round + 1) : 
                print(f"\nRound {i} of {round}")
                user = self.get_user_input()
                pc = self.get_pc()
                
                print(f"PC choice : {pc}")
                winner = self.decide_winner(user,pc)
                
                if winner == "draw":
                    print (f"It is {winner} 🫱🏼‍🫲🏼")
                elif winner == "user":
                    print(f"{winner} wins 🏆")
                else:
                    print(f"{winner} wins 🖥️")
                
                print(f"\n++++Score++++ \nYou: {self.user} 👤\nPC: {self.pc} 🖥️\n++++")

            print("\n====Final Result===\n")
            if self.user > self.pc:
                print("🎉 You Win the Game!")
            elif self.user < self.pc:
                print("💻 PC Wins the Game!")
            else:
                 print("🤝 It's a Draw!")
            
            print("Thanks for playing!")
        
        except KeyboardInterrupt:
            print("\n⛔ Game interrupted by user.")
        except Exception as e:
            print("An unexpected error occurred : ",e)
     
     
try:
    game = StonePaperScissors()
    game.play()
except Exception as e:
    print("Critical error : ",e)       
            

