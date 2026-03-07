from manim import *

class MathSolution(Scene):
    def construct(self):
        title = Text('Normal Matrix Theorem', font_size=40).to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)

        defn = MathTex(r'AA^\dagger = A^\dagger A', font_size=36, color=BLUE)
        self.play(FadeIn(defn))
        self.wait(1)

        self.play(FadeOut(defn))
        eq = MathTex(r'A = UDU^\dagger', font_size=36, color=BLUE)
        self.play(Write(eq))
        self.wait(1)

        self.play(FadeOut(eq))
        answer = MathTex(r'A \\ \text{is unitarily diagonalizable}', font_size=44, color=GREEN)
        box = SurroundingRectangle(answer, color=GREEN, buff=0.2)
        self.play(FadeIn(answer), Create(box))
        self.wait(2)
