declare module "d3-regression" {
  type Point = [number, number]

  interface RegressionOp {
    (data: unknown[]): Point[]
    x(fn: (d: unknown) => number): this
    y(fn: (d: unknown) => number): this
    domain(domain?: [number, number]): this
  }

  interface LoessRegressionOp extends RegressionOp {
    bandwidth(bw: number): this
  }

  export function regressionLinear(): RegressionOp
  export function regressionLoess(): LoessRegressionOp
  export function regressionPoly(): RegressionOp
  export function regressionExp(): RegressionOp
  export function regressionLog(): RegressionOp
  export function regressionPow(): RegressionOp
  export function regressionQuad(): RegressionOp
}
