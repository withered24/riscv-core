// tb_top.sv — simulation top level: the core wired to sim_mem
//
// cocotb drives clk/rst and reads the trace_* signals from here.

module tb_top #(
    parameter logic [31:0] RESET_PC = 32'h0000_0000   // riscv-tests use 0x8000_0000
) (
    input  logic        clk,
    input  logic        rst,

    output logic        trace_valid,
    output logic [31:0] trace_pc,
    output logic [31:0] trace_instr,
    output logic        trace_rd_we,
    output logic [4:0]  trace_rd,
    output logic [31:0] trace_rd_wdata,
    output logic        trace_illegal,
    output logic        trace_trap,
    output logic [31:0] trace_cause,
    output logic [31:0] dmem_addr,
    output logic [31:0] dmem_wdata,
    output logic [3:0]  dmem_wstrb
);

    logic [31:0] imem_addr, imem_rdata, dmem_rdata;

    core #(.RESET_PC(RESET_PC)) u_core (
        .clk            (clk),
        .rst            (rst),
        .imem_addr      (imem_addr),
        .imem_rdata     (imem_rdata),
        .dmem_addr      (dmem_addr),
        .dmem_wdata     (dmem_wdata),
        .dmem_wstrb     (dmem_wstrb),
        .dmem_rdata     (dmem_rdata),
        .trace_valid    (trace_valid),
        .trace_pc       (trace_pc),
        .trace_instr    (trace_instr),
        .trace_rd_we    (trace_rd_we),
        .trace_rd       (trace_rd),
        .trace_rd_wdata (trace_rd_wdata),
        .trace_illegal  (trace_illegal),
        .trace_trap     (trace_trap),
        .trace_cause    (trace_cause)
    );

    sim_mem u_mem (
        .clk    (clk),
        .iaddr  (imem_addr),
        .irdata (imem_rdata),
        .daddr  (dmem_addr),
        .dwdata (dmem_wdata),
        .dwstrb (dmem_wstrb),
        .drdata (dmem_rdata)
    );

endmodule
