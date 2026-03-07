from manim import *

class MathSolution(Scene):
    def construct(self):
        # 1. Title
        title = Text("Solve for x: 7 = 2x + 12 - 2", font_size=40).to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)

        # 2. Show problem
        problem = MathTex(r"7 = 2x + 12 - 2", font_size=36).next_to(title, DOWN, buff=0.5)
        self.play(FadeIn(problem))
        self.wait(1)

        # 3. Solution steps (clear previous, show new)
        self.play(FadeOut(problem))
        step1 = MathTex(r"7 = 2x + 12 - 2", font_size=36)
        step1_simplified = MathTex(r"7 = 2x + 10", font_size=36)
        self.play(Write(step1))
        self.wait(1)
        self.play(Transform(step1, step1_simplified))
        self.wait(1)

        self.play(FadeOut(step1))
        step2 = MathTex(r"7 = 2x + 10", font_size=36)
        step2_result = MathTex(r"-3 = 2x", font_size=36)
        self.play(Write(step2))
        self.wait(1)
        self.play(Transform(step2, step2_result))
        self.wait(1)

        self.play(FadeOut(step2))
        step3 = MathTex(r"-3 = 2x", font_size=36)
        step3_result = MathTex(r"x = -\frac{3}{2}", font_size=36)
        self.play(Write(step3))
        self.wait(1)
        self.play(Transform(step3, step3_result))
        self.wait(1)

        # Final answer with box
        answer = MathTex(r"x = -\frac{3}{2}", color=GREEN, font_size=44)
        box = SurroundingRectangle(answer, color=GREEN, buff=0.2)
        self.play(FadeIn(answer), Create(box))
        self.wait(2)