local mg     = require "moongen"
local memory = require "memory"
local device = require "device"
local ts     = require "timestamping"
local stats  = require "stats"
local hist   = require "histogram"

local ETH_DST	= "11:12:13:14:15:16"

local function getRstFile(...)
	local args = { ... }
	for i, v in ipairs(args) do
		result, count = string.gsub(v, "%-%-result%=", "")
		if (count == 1) then
			return i, result
		end
	end
	return nil, nil
end

function configure(parser)
	parser:description("Generates bidirectional CBR traffic with hardware rate control and measure latencies.")
	parser:argument("dev1", "Device to transmit/receive from."):convert(tonumber)
	parser:argument("dev2", "Device to transmit/receive from."):convert(tonumber)
	parser:option("-r --rate", "Transmit rate in Mbit/s."):default(10000):convert(tonumber)
	parser:option("-p --pktrate", "Transmit rate in pps."):default(0):convert(tonumber)
	parser:option("-s --pktsize", "Packetsize in bytes (incl. crc)."):default(64):convert(tonumber)
	parser:option("-f --file", "Filename of the latency histogram."):default("histogram.csv")
	parser:option("-f --flows", "Number of different IPs to use."):default(100):convert(tonumber)
	parser:option("-t --table-entries", "Number of different table entries."):default(4):convert(tonumber)
end

function master(args)
	local dev1 = device.config({port = args.dev1, txQueues = 5})
	local dev2 = device.config({port = args.dev2, rxQueues = 2})
	device.waitForLinks()

	pktsize = args.pktsize
	if args.pktsize < 64 then
		pktsize = 64
	end

	rate = args.rate
	if args.pktrate > 0 then
		rate = (args.pktrate * (pktsize) * 8) / 1000000
	end
	rate = rate / 4
	dev1:getTxQueue(0):setRate(rate)
	dev1:getTxQueue(1):setRate(rate)
	dev1:getTxQueue(2):setRate(rate)
	dev1:getTxQueue(3):setRate(rate)

	mg.startTask("txrxCounterSlave", dev1, dev2)

	mg.startTask("loadSlave", dev1:getTxQueue(0), pktsize, args.flows, args.table_entries)
	mg.startTask("loadSlave", dev1:getTxQueue(1), pktsize, args.flows, args.table_entries)
	mg.startTask("loadSlave", dev1:getTxQueue(2), pktsize, args.flows, args.table_entries)
	mg.startTask("loadSlave", dev1:getTxQueue(3), pktsize, args.flows, args.table_entries)

	mg.startSharedTask("timerSlave", dev1:getTxQueue(4), dev2:getRxQueue(1), args.file)
	mg.waitForTasks()
end

function loadSlave(txQueue, pktsize, flows, table_entries)
	local baseIP = parseIPAddress("10.0.0.1")
	local mem = memory.createMemPool(function(buf)
		buf:getIP4Packet():fill{ 
			ethSrc = queue,
			ethDst = "12:34:56:78:9a:bc",
			pktLength = pktsize
		}
	end)
	local bufs = mem:bufArray()
	local counter = 0
	local te_counter = 0
	while mg.running() do
		bufs:alloc(pktsize - 4)
		for i, buf in ipairs(bufs) do 			
			local pkt = buf:getIP4Packet()
                        pkt.ip4.src:set(baseIP + counter)
                        for j = {{ payload_u32_offset }},{{ payload_u32_offset + 3 }},1 do
                                pkt.payload.uint32[j] = te_counter
                        end
                        te_counter = incAndWrap(te_counter, table_entries)
                        counter = incAndWrap(counter, flows)
		end 
		txQueue:send(bufs)
	end
end

function timerSlave(txQueue, rxQueue, histfile)
	local timestamper = ts:newTimestamper(txQueue, rxQueue)
	local hist = hist:new()
	mg.sleepMillis(1000) -- ensure that the load task is running
	while mg.running() do
		hist:update(timestamper:measureLatency(function(buf) buf:getEthernetPacket().eth.dst:setString(ETH_DST) end))
	end
	hist:print()
	hist:save(histfile)
end

function txrxCounterSlave(txDev, rxDev)
        print("Started TX/RX counter")

        local txCtr = stats:newDevTxCounter(txDev, "csv", "throughput-tx.csv")
        local rxCtr = stats:newDevRxCounter(rxDev, "csv", "throughput-rx.csv")

        while mg.running() do
                txCtr:update()
                rxCtr:update()
        end

        txCtr:finalize()
        rxCtr:finalize()
end
