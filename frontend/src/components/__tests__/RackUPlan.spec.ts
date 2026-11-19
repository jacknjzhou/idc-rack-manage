import { mount, flushPromises } from "@vue/test-utils"
import { describe, it, expect, vi } from "vitest"
import RackUPlan from "../RackUPlan.vue"

vi.mock("../../api", () => ({
  apiGet: vi.fn(async (url: string) => {
    if (url.includes("/uplan/")) return { A: [null, {asset_no:"D1",status:"active"}, {asset_no:"D1",status:"active"}], B: [null,null,null] }
    return { remaining_u_by_face: {A:1,B:3}, remaining_power_w: 3800,
             remaining_weight_kg: 785, load_ratio: 0.9, warnings: ["负载率告警"] }
  })
}))

describe("RackUPlan", () => {
  it("渲染U位格子与资产编号", async () => {
    const w = mount(RackUPlan, { props: { rackId: 1 } })
    await flushPromises()
    expect(w.findAll(".u-cell").length).toBe(6)
    expect(w.text()).toContain("D1")
    expect(w.text()).toContain("负载率告警")
  })
})
