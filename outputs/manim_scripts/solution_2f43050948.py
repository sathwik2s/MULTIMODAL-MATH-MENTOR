from manim import *

class MathSolution(Scene):
    def construct(self):
        # 1. Title
        title = Text("Scalar Triple Product", font_size=40).to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)

        # 2. Show problem
        problem = MathTex(r"A \cdot (B \times C, font_size=36)", font_size=36).next_to(title, DOWN, buff=0.5)
        self.play(FadeIn(problem))
        self.wait(1)

        # 3. Define vectors A, B, and C
        vectors = VGroup(
            MathTex(r"A = (1, 2, 3, font_size=36)", font_size=36),
            MathTex(r"B = (2, 4, 6, font_size=36)", font_size=36),
            MathTex(r"C = (1, 0, -1, font_size=36)", font_size=36)
        ).arrange(DOWN, buff=0.4)
        self.play(FadeOut(problem), Write(vectors))
        self.wait(1)

        # 4. Calculate the cross product of vectors B and C
        cross_product = MathTex(r"B \times C = \begin{vmatrix} i & j & k \\ 2 & 4 & 6 \\ 1 & 0 & -1 \end{vmatrix}", font_size=36)
        self.play(FadeOut(vectors), Write(cross_product))
        self.wait(1)

        # 5. Expand the determinant to find the components of the cross product
        expanded_cross_product = VGroup(
            MathTex(r"B \times C = i(4(-1, font_size=36) - 6(0)) - j(2(-1) - 6(1)) + k(2(0) - 4(1))", font_size=36),
            MathTex(r"B \times C = i(-4, font_size=36) - j(-2 - 6) + k(-4)", font_size=36),
            MathTex(r"B \times C = (-4, 8, -4, font_size=36)", font_size=36)
        ).arrange(DOWN, buff=0.4)
        self.play(FadeOut(cross_product), Write(expanded_cross_product))
        self.wait(1)

        # 6. Calculate the dot product of vector A and the result of the cross product of B and C
        dot_product = VGroup(
            MathTex(r"A \cdot (B \times C, font_size=36) = 1(-4) + 2(6 + 2) + 3(-4)", font_size=36),
            MathTex(r"A \cdot (B \times C, font_size=36) = -4 + 16 - 12", font_size=36),
            MathTex(r"A \cdot (B \times C, font_size=36) = 0", font_size=36)
        ).arrange(DOWN, buff=0.4)
        self.play(FadeOut(expanded_cross_product), Write(dot_product))
        self.wait(1)

        # 7. Final answer with box
        answer = MathTex(r"0", color=GREEN, font_size=44)
        box = SurroundingRectangle(answer, color=GREEN, buff=0.2)
        self.play(FadeOut(dot_product), FadeIn(answer), Create(box))
        self.wait(2)