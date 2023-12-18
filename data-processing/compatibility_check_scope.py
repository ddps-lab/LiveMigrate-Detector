import pandas as pd
from pathlib import Path

currentPath = str(Path(__file__).resolve().parent)

def get_ISAs(isa = None):
    ISAs = ["xsave", "aes", "clfsh", "cmpxchg16b", "fxsave", "fxsave64", "lahf", "longmode", "movbe", "pclmulqdq",
            "pentiummmx", "popcnt", "prefetchw", "rdtscp", "smx", "sse", "sse2", "sse2mmx", "sse3", "sse3x87", "monitor",
            "sse4", "sse42", "ssemxcsr", "ssse3", "ssse3mmx", "vtx", "cmov", "fcmov", "fcomi", "serialize", "keylocker",
            "keylocker_wide", "avx512_vp2intersect_128", "avx512_vp2intersect_256", "avx512_vp2intersect_512", "avx512f_128",
            "avx512f_128n", "avx512f_256", "avx512f_512", "avx512f_kop", "avx512f_scalar", "icache_prefetch", "avx2",
            "avx2gather", "fma", "avx_vnni_int8", "avx512_vbmi2_128", "avx512_vbmi2_256", "avx512_vbmi2_512", "avx512_fp16_128n",
            "avx512_fp16_128", "avx512_fp16_256", "avx512_fp16_512", "avx512_fp16_scalar", "rdrand", "avx_vnni", "avx_ifma",
            "avx512_4fmaps_512", "avx512_4fmaps_scalar", "pku", "xsaveopt", "cmpccxadd", "cldemote", "wrmsrns", "clflushopt",
            "avx512_bf16_128", "avx512_bf16_256", "avx512_bf16_512", "amx_tile", "amx_int8", "amx_bf16", "cet", "avx_ne_convert",
            "bmi1", "bmi2", "avx512_bitalg_128", "avx512_bitalg_256", "avx512_bitalg_512", "ptwrite", "avx512_vbmi_128",
            "avx512_vbmi_256", "avx512_vbmi_512", "avx512_vpopcntdq_128", "avx512_vpopcntdq_256", "sha", "adox_adcx", "smap",
            "avx_gfni", "avx512_gfni_128", "avx512_gfni_256", "avx512_gfni_512", "avx512_vaes_128", "avx512_vaes_256",
            "avx512_vaes_512", "avx512_vpclmulqdq_128", "avx512_vpclmulqdq_256", "avx512_vpclmulqdq_512", "movdir",
            "avx512_vpopcntdq_512", "avx512_vnni_128", "avx512_vnni_256", "avx512_vnni_512", "enqcmd", "mpx", "avx",
            "avxaes", "avx512er_512", "avx512er_scalar", "avx512pf_512", "prefetchwt1", "avx512cd_128", "avx512cd_256",
            "avx512cd_512", "pconfig", "waitpkg", "clwb", "wbnoinvd", "rdseed", "xsaves", "amx_complex", "uintr", "avx512bw_128",
            "avx512bw_128n", "avx512bw_256", "avx512bw_512", "avx512bw_kop", "avx512dq_128", "avx512dq_128n", "avx512dq_256",
            "avx512dq_512", "avx512dq_kop", "avx512dq_scalar", "avx512_4vnniw_512", "f16c", "msrlist", "xsavec", "rdwrfsgs",
            "avx512_ifma_128", "avx512_ifma_256", "avx512_ifma_512", "tsx_ldtrk", "hreset", "amx_fp16", "sgx", "rtm", "invpcid",
            "lzcnt", "rdpid", "rao_int", 'xtest']
    
    temp = ['longmode', 'avx512f_128', 'avx512bw_256', 'avx512bw_kop', 'bmi1', 'avx512f_256', 'bmi2', 'sse', 'avx512f_128n', 'avx', 'sse2', 'cmov', 'ssse3', 'sha', 'avx2', 'ssemxcsr', 'avx512bw_128', 'avx512dq_kop', 'avx512f_kop', 'sse42']
    temp = [item.lower() for item in temp]

    available = set()
    for i in temp:
        if i.split('_')[0] == 'avx512f':
            available.add('avx512f')
            continue
        
        if i.split('_')[0] == 'avx512bw':
            available.add('avx512bw')
            continue

        if i.split('_')[0] == 'avx512dq':
            available.add('avx512dq')
            continue

        if i.split('_')[0] == 'ssemxcsr':
            available.add('sse')
            continue

        if i.split('_')[0] == 'fcmov':
            available.add('cmov')
            continue

        if i.split('_')[0] == 'sse3x87':
            available.add('sse3')
            continue

        if i.split('_')[0] == 'avx2gather':
            available.add('avx2')
            continue

        if i.split('_')[0] == 'avxaes':
            if 'avx' in temp and 'aes' in temp:
                continue
            else:
                print('error!')

        if i in ISAs:
            available.add(i)
    
    print(available)
    
get_ISAs()