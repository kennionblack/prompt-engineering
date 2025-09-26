#!/usr/bin/env python3
import random

def play_game(max_num=100):
    secret = random.randint(1, max_num)
    attempts = 0
    print(f"I'm thinking of a number between 1 and {max_num}. Try to guess it!")

    while True:
        guess_str = input("Your guess: ").strip()
        try:
            guess = int(guess_str)
        except ValueError:
            print("Please enter a valid integer.")
            continue

        if not (1 <= guess <= max_num):
            print(f"Please guess a number between 1 and {max_num}.")
            continue

        attempts += 1
        if guess < secret:
            print("Too low.")
        elif guess > secret:
            print("Too high.")
        else:
            print(f"Correct! You guessed the number in {attempts} attempt{'s' if attempts != 1 else ''}.")
            break


def main():
    print("Welcome to the Number Guessing Game!")
    while True:
        max_input = input("Enter the maximum number (press Enter for 100): ").strip()
        if max_input == "":
            max_num = 100
        else:
            try:
                max_num = int(max_input)
                if max_num < 2:
                    print("Please enter a number >= 2.")
                    continue
            except ValueError:
                print("Please enter a valid integer.")
                continue

        play_game(max_num)

        again = input("Play again? (y/n): ").strip().lower()
        if not again.startswith('y'):
            print("Thanks for playing. Goodbye!")
            break

if __name__ == "__main__":
    main()
