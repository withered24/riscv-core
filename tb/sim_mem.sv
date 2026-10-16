// sim_mem.sv — simulation-only unified memory (code + data in one array)
//
// Combinational reads on both ports, byte-enabled synchronous write.
// The address is taken modulo the memory size, so a program linked at
// 0x8000_0000 (where riscv-tests live) lands at index 0 too.
// The testbench loads programs by writing `mem` directly through cocotb.

module sim_mem #(
    parameter int WORDS = 16384           // 64 KiB
) (
    input  logic        clk,

    input  logic [31:0] iaddr,
    output logic [31:0] irdata,

    input  logic [31:0] daddr,
    input  logic [31:0] dwdata,
    input  logic [3:0]  dwstrb,
    output logic [31:0] drdata
);

    localparam int AW = $clog2(WORDS);

    logic [31:0] mem [0:WORDS-1];

    initial begin
        for (int i = 0; i < WORDS; i++) mem[i] = 32'd0;
    end

    assign irdata = mem[iaddr[AW+1:2]];
    assign drdata = mem[daddr[AW+1:2]];

    always_ff @(posedge clk) begin
        for (int b = 0; b < 4; b++)
            if (dwstrb[b]) mem[daddr[AW+1:2]][8*b +: 8] <= dwdata[8*b +: 8];
    end

endmodule
