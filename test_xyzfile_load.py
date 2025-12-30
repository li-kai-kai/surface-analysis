from process_xyz import process_xyz

result = process_xyz("example/005-avg.xyz", "output/test_xyzfile.txt", edge_clearance=0)
if result:
    print(f"\n✓ Success!")
    print(f"PV: {result['pv'] * 1e6:.2f}um")
    print(f"SFMA: {result['sfma'] * 1e9:.2f}nm")
else:
    print("× Failed")
