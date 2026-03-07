from manim import *

class MathSolution(Scene):
    def construct(self):
        # 1. Title
        title = Text("Quadratic Equation Solution", font_size=40).to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)

        # 2. Show problem
        problem = MathTex(r"x^2 + 2x + 5", font_size=36).next_to(title, DOWN, buff=0.5)
        self.play(FadeIn(problem))
        self.wait(1)

        # 3. Solution steps (clear previous, show new)
        self.play(FadeOut(problem))
        step1 = Text("Identify the equation as a quadratic equation", font_size=36)
        self.play(Write(step1))
        self.wait(0.5)
        formula = MathTex(r"ax^2 + bx + c = 0", color=BLUE, font_size=36).next_to(step1, DOWN, buff=0.4)
        self.play(Write(formula))
        result = MathTex(r"a = 1, b = 2, c = 5", font_size=36).next_to(formula, DOWN, buff=0.4)
        self.play(Write(result))
        self.wait(1)

        self.play(FadeOut(step1), FadeOut(formula), FadeOut(result))
        step2 = Text("Calculate the discriminant", font_size=36)
        self.play(Write(step2))
        self.wait(0.5)
        formula2 = MathTex(r"D = b^2 - 4ac", color=BLUE, font_size=36).next_to(step2, DOWN, buff=0.4)
        self.play(Write(formula2))
        calculation = MathTex(r"D = 2^2 - 4*1*5 = -16", font_size=36).next_to(formula2, DOWN, buff=0.4)
        self.play(Write(calculation))
        self.wait(1)

        self.play(FadeOut(step2), FadeOut(formula2), FadeOut(calculation))
        step3 = Text("Apply the quadratic formula", font_size=36)
        self.play(Write(step3))
        self.wait(0.5)
        formula3 = MathTex(r"x = (-b ± √(b^2 - 4ac, font_size=36)) / (2a)", color=BLUE, font_size=36).next_to(step3, DOWN, buff=0.4)
        self.play(Write(formula3))
        result2 = MathTex(r"x = (-2 ± √(-16, font_size=36)) / 2 = -1 ± 2i", font_size=36).next_to(formula3, DOWN, buff=0.4)
        self.play(Write(result2))
        self.wait(1)

        # Final answer with box
        self.play(FadeOut(step3), FadeOut(formula3), FadeOut(result2))
        answer = MathTex(r"-1 - 2i, -1 + 2i", color=GREEN, font_size=44)
        box = SurroundingRectangle(answer, color=GREEN, buff=0.2)
        self.play(FadeIn(answer), Create(box))
        self.wait(2)