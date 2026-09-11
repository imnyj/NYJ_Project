with open('/home/imnyj/Workspace/paper1/writer/final/main.tex', 'r') as f:
    content = f.read()

# Fix 1
content = content.replace(
    'The networking layer of the simulation implements specific communication parameters to govern the Vehicle-to-Infrastructure (V2I) interactions. Each Road-Side Unit (RSU) is positioned at the geometric center of major intersections',
    'The networking layer of the simulation implements specific communication parameters to govern the V2I interactions. Each RSU is positioned at the geometric center of major intersections'
)

# Fix 2
content = content.replace(
    'In Content-Centric Vehicular Networks, Road-Side Units (RSUs) act as edge caching nodes',
    'In Content-Centric Vehicular Networks (CCVNs), Road-Side Units (RSUs) act as edge caching nodes'
)

with open('/home/imnyj/Workspace/paper1/writer/final/main.tex', 'w') as f:
    f.write(content)
