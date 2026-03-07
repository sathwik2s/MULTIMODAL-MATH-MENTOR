from manim import *

class MathSolution(Scene):
    def construct(self):
        # Step 1: Define normal matrices and unitary diagonalization
        title = Text("Unitary Diagonalization and Normal Matrices")
        self.play(Write(title))
        self.wait(1)
        self.play(FadeOut(title))

        normal_matrices = Text("Normal Matrices: A*A^† = A^†*A")
        normal_matrices.set_color(BLUE)
        self.play(Write(normal_matrices))
        self.wait(1)

        unitary_diagonalization = Text("Unitary Diagonalization: U*A*U^† = D")
        unitary_diagonalization.set_color(BLUE)
        self.play(Write(unitary_diagonalization))
        self.wait(1)
        self.play(FadeOut(normal_matrices), FadeOut(unitary_diagonalization))

        # Step 2: Prove normal matrices are unitarily diagonalizable
        spectral_theorem = MathTex(r"A = U*D*U^†")
        spectral_theorem.set_color(BLUE)
        self.play(Write(spectral_theorem))
        self.wait(1)
        self.play(FadeOut(spectral_theorem))

        normal_diagonalizable = Text("Normal Matrices are Unitarily Diagonalizable")
        normal_diagonalizable.set_color(GREEN)
        self.play(Write(normal_diagonalizable))
        self.wait(1)
        self.play(FadeOut(normal_diagonalizable))

        # Step 3: Prove unitarily diagonalizable matrices are normal
        unitary_diagonalizable_normal = MathTex(r"A = U*D*U^† \implies A*A^† = A^†*A")
        unitary_diagonalizable_normal.set_color(BLUE)
        self.play(Write(unitary_diagonalizable_normal))
        self.wait(1)
        self.play(FadeOut(unitary_diagonalizable_normal))

        diagonalizable_normal = Text("Unitarily Diagonalizable Matrices are Normal")
        diagonalizable_normal.set_color(GREEN)
        self.play(Write(diagonalizable_normal))
        self.wait(1)
        self.play(FadeOut(diagonalizable_normal))

        # Final Answer
        final_answer = MathTex(r"A \text{ is unitarily diagonalizable } \iff A \text{ is normal}")
        final_answer.set_color(YELLOW)
        self.play(Write(final_answer))
        self.wait(2)